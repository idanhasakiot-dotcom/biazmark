"""Placeholder media provider — always configured.

Generates a deterministic SVG with the first words of the prompt so the pipeline
produces something visual even without any media-gen keys. Drop-in substitute
that keeps the loop unblocked during development / Free tier.
"""
from __future__ import annotations

import hashlib
import pathlib
import uuid
from textwrap import shorten

from app.config import get_settings
from app.media.base import BaseMediaProvider, MediaResult

_SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#g)"/>
  <text x="50%" y="50%" font-family="Inter, sans-serif" font-size="{fs}" fill="white"
        text-anchor="middle" dominant-baseline="middle" font-weight="600">
    {label}
  </text>
  <text x="50%" y="{bottom}" font-family="Inter, sans-serif" font-size="18" fill="#ffffff99"
        text-anchor="middle">biazmark · placeholder</text>
</svg>
"""


class PlaceholderMedia(BaseMediaProvider):
    name = "placeholder"

    def is_configured(self) -> bool:
        return True

    async def generate(
        self, prompt: str, *, aspect: str = "1:1", kind: str = "image"
    ) -> MediaResult:
        w, h = _dims(aspect)
        c1, c2 = _palette(prompt)
        label = shorten(prompt, width=80, placeholder="…") or "biazmark"
        svg = _SVG_TEMPLATE.format(
            w=w, h=h, c1=c1, c2=c2,
            label=_xml_escape(label),
            fs=max(24, w // 20),
            bottom=h - 40,
        )
        settings = get_settings()
        target = pathlib.Path(settings.media_storage_dir)
        target.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.svg"
        (target / fname).write_text(svg, encoding="utf-8")
        public = f"{settings.media_public_base.rstrip('/')}/{fname}"
        return MediaResult(kind="image", url=public, local_path=str(target / fname),
                           width=w, height=h, provider=self.name, prompt=prompt)


def _dims(aspect: str) -> tuple[int, int]:
    return {"1:1": (1024, 1024), "4:5": (1024, 1280),
            "16:9": (1536, 864), "9:16": (864, 1536)}.get(aspect, (1024, 1024))


def _palette(seed: str) -> tuple[str, str]:
    h = hashlib.sha1(seed.encode()).hexdigest()
    c1 = "#" + h[:6]
    c2 = "#" + h[6:12]
    return c1, c2


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&apos;"))
