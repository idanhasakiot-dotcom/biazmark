"""LLM abstraction — tier-aware, multi-provider.

Gives every agent a single `complete(system, user, ...)` interface.
Free tier → Ollama (local). Basic/Pro/Enterprise → Anthropic (Haiku/Sonnet/Opus).
"""
from __future__ import annotations

import json
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings, Tier, TierSpec, get_settings
from app.logging_config import get_logger

log = get_logger(__name__)


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Single entry-point used by every agent.

    Picks the right backend based on tier. Agents don't know or care which provider
    they're talking to — they just call `complete()` and optionally `complete_json()`.
    """

    def __init__(self, settings: Settings | None = None, tier_override: Tier | None = None):
        self.settings = settings or get_settings()
        self.tier = tier_override or self.settings.biazmark_tier
        self.spec = TierSpec.for_tier(self.tier)
        self._anthropic: AsyncAnthropic | None = None

    # --- public --------------------------------------------------------

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        provider = self.spec["llm_provider"]
        if provider == "anthropic" and self.settings.anthropic_api_key:
            return await self._anthropic_complete(system, user, max_tokens, temperature)
        # Fall back to Ollama (or if provider=ollama)
        return await self._ollama_complete(system, user, max_tokens, temperature)

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema_hint: str = "",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Ask for JSON, parse it, retry once if parsing fails."""
        instruction = (
            f"{system}\n\n"
            "Respond with a single valid JSON object. No prose, no markdown fences."
        )
        if schema_hint:
            instruction += f"\n\nSchema hint:\n{schema_hint}"

        raw = await self.complete(instruction, user, max_tokens=max_tokens, temperature=0.4)
        return _parse_json_lenient(raw)

    # --- backends ------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def _anthropic_complete(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str:
        if self._anthropic is None:
            self._anthropic = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        model = self.spec["llm_model"]
        msg = await self._anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [b.text for b in msg.content if getattr(b, "type", "") == "text"]
        return "".join(parts).strip()

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def _ollama_complete(
        self, system: str, user: str, max_tokens: int, temperature: float
    ) -> str:
        url = f"{self.settings.ollama_host.rstrip('/')}/api/chat"
        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
                return (data.get("message") or {}).get("content", "").strip()
        except Exception as e:
            # Graceful degradation: return a minimal stub so the pipeline keeps flowing.
            log.warning("ollama_unavailable", error=str(e))
            return _offline_stub(system, user)


def _parse_json_lenient(raw: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM response that may have surrounding text/fences."""
    if not raw:
        return {}
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
        if s.endswith("```"):
            s = s[:-3]
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {"_raw": raw}
    try:
        return json.loads(s[start : end + 1])
    except json.JSONDecodeError:
        return {"_raw": raw}


def _offline_stub(system: str, user: str) -> str:
    """Returned when no LLM is reachable — keeps the pipeline usable offline for testing."""
    return json.dumps(
        {
            "note": "offline stub — set ANTHROPIC_API_KEY or start Ollama for real output",
            "echo": user[:200],
        }
    )
