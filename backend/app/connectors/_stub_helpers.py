"""Helper for platform connectors that aren't fully implemented yet.

Returns clean "not configured" responses so the UI and optimizer can reason about
availability. Drop the stub behaviour once the real API integration is wired in.
"""
from __future__ import annotations

from typing import Any

from app.connectors.base import ConnectionStatus, Metric, PublishResult


def not_configured_status(platform: str) -> ConnectionStatus:
    return ConnectionStatus(
        connected=False,
        error=f"{platform} connector is declared but credentials/implementation not set up",
    )


def not_configured_publish(platform: str, variant: dict[str, Any]) -> PublishResult:
    return PublishResult(
        external_id=f"{platform}_notconfigured",
        raw={"skipped": True, "reason": "connector not configured", "headline": variant.get("headline", "")},
    )


def zero_metrics(external_ids: list[str]) -> list[Metric]:
    return [Metric(external_id=eid, raw={"skipped": True}) for eid in external_ids]
