"""OpenAI image generation (DALL-E 3 / gpt-image-1)."""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.media.base import BaseMediaProvider, MediaResult


class OpenAIMedia(BaseMediaProvider):
    name = "openai"

    def is_configured(self) -> bool:
        return bool(get_settings().openai_api_key)

    async def generate(
        self, prompt: str, *, aspect: str = "1:1", kind: str = "image"
    ) -> MediaResult:
        key = get_settings().openai_api_key
        size = _size_for_aspect(aspect)
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "gpt-image-1", "prompt": prompt[:4000], "size": size, "n": 1},
            )
            r.raise_for_status()
            data = r.json()["data"][0]
        remote_url = data.get("url")
        if not remote_url and data.get("b64_json"):
            # Save base64 locally as fallback path.
            import base64
            import pathlib
            import uuid

            from app.config import get_settings as _s
            settings = _s()
            target = pathlib.Path(settings.media_storage_dir)
            target.mkdir(parents=True, exist_ok=True)
            fname = f"{uuid.uuid4().hex}.png"
            (target / fname).write_bytes(base64.b64decode(data["b64_json"]))
            public = f"{settings.media_public_base.rstrip('/')}/{fname}"
            return MediaResult(kind="image", url=public, local_path=str(target / fname),
                               provider=self.name, prompt=prompt)
        local, public = await self._download(remote_url or "", ext="png")
        w, h = _aspect_to_wh(aspect)
        return MediaResult(kind="image", url=public, local_path=local, width=w, height=h,
                           provider=self.name, prompt=prompt, meta=data)


def _size_for_aspect(a: str) -> str:
    a = a.strip()
    return {"1:1": "1024x1024", "4:5": "1024x1280", "16:9": "1536x1024", "9:16": "1024x1536"}.get(a, "1024x1024")


def _aspect_to_wh(a: str) -> tuple[int, int]:
    s = _size_for_aspect(a)
    w, h = s.split("x")
    return int(w), int(h)
