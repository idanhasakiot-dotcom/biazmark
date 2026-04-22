"""Connector plugin system.

Any class in this package that subclasses `BaseConnector` auto-registers on import.
The registry is used by the campaign engine to publish content and fetch metrics.
"""
from __future__ import annotations

from app.connectors import blog as _blog  # noqa: F401
from app.connectors import email as _email  # noqa: F401
from app.connectors import google_ads as _google_ads  # noqa: F401
from app.connectors import linkedin as _linkedin  # noqa: F401
from app.connectors import meta as _meta  # noqa: F401

# Import submodules to trigger registration.
from app.connectors import preview as _preview  # noqa: F401
from app.connectors import tiktok as _tiktok  # noqa: F401
from app.connectors import x as _x  # noqa: F401
from app.connectors.base import BaseConnector, ConnectorRegistry, registry

__all__ = ["BaseConnector", "ConnectorRegistry", "registry"]
