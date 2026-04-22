"""Media generation providers — images (now) and video (where available)."""
from __future__ import annotations

# Trigger registrations.
from app.media import openai as _openai  # noqa: F401
from app.media import placeholder as _placeholder  # noqa: F401
from app.media import replicate as _replicate  # noqa: F401
from app.media import stability as _stability  # noqa: F401
from app.media.base import BaseMediaProvider, MediaResult, media_registry

__all__ = ["BaseMediaProvider", "MediaResult", "media_registry"]
