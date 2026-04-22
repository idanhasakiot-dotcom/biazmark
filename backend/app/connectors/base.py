"""Base connector interface + singleton registry.

A connector is the adapter between an internal `ContentVariant` and an external
platform (Meta, Google Ads, LinkedIn, TikTok, X, email, ...). Every connector
implements four operations:

    connect(credentials) -> ConnectionStatus
    publish(variant, campaign) -> PublishResult   # returns external_id
    fetch_metrics(external_ids) -> list[Metric]   # pull current stats
    disconnect() -> None

Add a new platform by:

    1. Creating a new file in app/connectors/<platform>.py
    2. Subclassing BaseConnector and setting `platform = "<name>"`
    3. Importing it in app/connectors/__init__.py

It auto-registers on import — no changes to the engine needed.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class PublishResult:
    external_id: str
    url: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Metric:
    external_id: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    engagement: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionStatus:
    connected: bool
    account_name: str = ""
    error: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """Inherit from this to add a new platform."""

    platform: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    supports_publish: ClassVar[bool] = True
    supports_metrics: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.platform and not cls.__name__.startswith("_"):
            registry.register(cls)

    def __init__(self, credentials: dict[str, Any] | None = None):
        self.credentials = credentials or {}

    @abstractmethod
    async def connect(self) -> ConnectionStatus:
        ...

    @abstractmethod
    async def publish(
        self,
        variant: dict[str, Any],
        campaign: dict[str, Any],
    ) -> PublishResult:
        ...

    @abstractmethod
    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        ...

    async def disconnect(self) -> None:  # override if needed
        return None


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, type[BaseConnector]] = {}

    def register(self, cls: type[BaseConnector]) -> None:
        self._connectors[cls.platform] = cls

    def get(self, platform: str) -> type[BaseConnector] | None:
        return self._connectors.get(platform)

    def instantiate(self, platform: str, credentials: dict[str, Any] | None = None) -> BaseConnector:
        cls = self.get(platform)
        if cls is None:
            raise KeyError(f"no connector registered for platform={platform!r}")
        return cls(credentials=credentials)

    def available(self) -> list[dict[str, Any]]:
        return [
            {
                "platform": c.platform,
                "display_name": c.display_name or c.platform,
                "supports_publish": c.supports_publish,
                "supports_metrics": c.supports_metrics,
            }
            for c in self._connectors.values()
        ]


registry = ConnectorRegistry()
