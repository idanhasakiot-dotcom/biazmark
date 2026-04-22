"""OAuth providers — one subclass per platform."""
from __future__ import annotations

from app.oauth import google as _google  # noqa: F401
from app.oauth import linkedin as _linkedin  # noqa: F401

# Trigger registrations.
from app.oauth import meta as _meta  # noqa: F401
from app.oauth import tiktok as _tiktok  # noqa: F401
from app.oauth import x as _x  # noqa: F401
from app.oauth.base import BaseOAuth, oauth_registry

__all__ = ["BaseOAuth", "oauth_registry"]
