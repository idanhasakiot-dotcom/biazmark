"""Stability AI image generation."""
from __future__ import annotations

import httpx

from app.config import get_settings
from app.media.base import BaseMediaProvider, MediaResult


class StabilityMedia(BaseMediaProvider):
    name = "stability"

    def is_configured(self) -> bool:
        return bool(get_settings().stability_api_key)

    async def generate(
        self, prompt: str, *, aspect: str = "1:1", kind: str = "image"
    ) -> MediaResult:
        key = get_settings().stability_api_key
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={"Authorization": f"Bearer {key}", "Accept": "image/*"},
                files={"prompt": (None, prompt[:3000]),
                       "aspect_ratio": (None, aspect),
                       "output_format": (None, "png")},
            )
            r.raise_for_status()
            content = r.content
        import pathlib
        import uuid
        settings = get_settings()
        target = pathlib.Path(settings.media_storage_dir)
        target.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.png"
        (target / fname).write_bytes(content)
        public = f"{settings.media_public_base.rstrip('/')}/{fname}"
        return MediaResult(kind="image", url=public, local_path=str(target / fname),
                           provider=self.name, prompt=prompt)
