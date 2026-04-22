"""Replicate media provider — runs FLUX.1 for images + video models on demand."""
from __future__ import annotations

import asyncio

import httpx

from app.config import get_settings
from app.media.base import BaseMediaProvider, MediaResult


class ReplicateMedia(BaseMediaProvider):
    name = "replicate"
    supports_video = True

    def is_configured(self) -> bool:
        return bool(get_settings().replicate_api_token)

    async def generate(
        self, prompt: str, *, aspect: str = "1:1", kind: str = "image"
    ) -> MediaResult:
        token = get_settings().replicate_api_token
        model = _model_for(kind)
        payload = {
            "input": {
                "prompt": prompt[:2000],
                "aspect_ratio": aspect,
                "output_format": "png" if kind == "image" else "mp4",
                "num_outputs": 1,
            }
        }
        async with httpx.AsyncClient(timeout=180) as c:
            r = await c.post(
                f"https://api.replicate.com/v1/models/{model}/predictions",
                headers={"Authorization": f"Token {token}",
                         "Content-Type": "application/json",
                         "Prefer": "wait"},
                json=payload,
            )
            r.raise_for_status()
            pred = r.json()
            # If still processing, poll.
            while pred.get("status") in ("starting", "processing"):
                await asyncio.sleep(2)
                rr = await c.get(
                    f"https://api.replicate.com/v1/predictions/{pred['id']}",
                    headers={"Authorization": f"Token {token}"},
                )
                rr.raise_for_status()
                pred = rr.json()
            output = pred.get("output")
            url = output[0] if isinstance(output, list) else output
        ext = "png" if kind == "image" else "mp4"
        local, public = await self._download(url or "", ext=ext)
        return MediaResult(kind=kind, url=public, local_path=local,
                           provider=self.name, prompt=prompt, meta=pred)


def _model_for(kind: str) -> str:
    if kind == "video":
        return "minimax/video-01"
    return "black-forest-labs/flux-schnell"
