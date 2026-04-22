"""Media generation base + registry.

Each provider implements:
    async def generate(prompt, *, aspect='1:1', kind='image') -> MediaResult

The registry picks the first provider whose `is_configured()` returns True; falls
back to the placeholder provider so the pipeline never blocks on missing keys.
"""
from __future__ import annotations

import pathlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

import aiofiles
import httpx

from app.config import get_settings


@dataclass
class MediaResult:
    kind: str  # image|video
    url: str
    local_path: str = ""
    width: int = 0
    height: int = 0
    provider: str = ""
    prompt: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


class BaseMediaProvider(ABC):
    name: ClassVar[str] = ""
    supports_video: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.name and not cls.__name__.startswith("_"):
            media_registry.register(cls)

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def generate(
        self, prompt: str, *, aspect: str = "1:1", kind: str = "image"
    ) -> MediaResult:
        ...

    # Shared helper: download a remote URL to local media dir and return path + public url.
    async def _download(self, url: str, ext: str = "png") -> tuple[str, str]:
        settings = get_settings()
        target_dir = pathlib.Path(settings.media_storage_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.{ext}"
        local = target_dir / fname
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(url)
            r.raise_for_status()
            async with aiofiles.open(local, "wb") as f:
                await f.write(r.content)
        public = f"{settings.media_public_base.rstrip('/')}/{fname}"
        return str(local), public


class _MediaRegistry:
    def __init__(self) -> None:
        self._providers: list[type[BaseMediaProvider]] = []

    def register(self, cls: type[BaseMediaProvider]) -> None:
        self._providers.append(cls)

    def pick(self, *, require_video: bool = False) -> BaseMediaProvider:
        """Pick the first configured provider.

        Order matters — we register OpenAI first, then Replicate, then Stability,
        and the placeholder last. If nothing is configured the placeholder always
        matches so the pipeline never blocks.
        """
        for cls in self._providers:
            inst = cls()
            if require_video and not inst.supports_video:
                continue
            if inst.is_configured():
                return inst
        # Fallback: placeholder (always configured).
        from app.media.placeholder import PlaceholderMedia
        return PlaceholderMedia()

    def all(self) -> list[dict[str, Any]]:
        out = []
        for cls in self._providers:
            inst = cls()
            out.append({
                "name": cls.name,
                "configured": inst.is_configured(),
                "supports_video": cls.supports_video,
            })
        return out


media_registry = _MediaRegistry()
