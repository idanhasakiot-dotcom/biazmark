"""Preview (dry-run) connector — the default for Free tier and for testing.

Does not touch any external API. Simulates publishing + returns stochastic metrics
that respond to variant quality (via the creator's predicted_strength score), so the
analyst/optimizer loop behaves realistically without any live credentials.
"""
from __future__ import annotations

import hashlib
import random
from typing import Any

from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult


class PreviewConnector(BaseConnector):
    platform = "preview"
    display_name = "Preview (dry-run)"

    async def connect(self) -> ConnectionStatus:
        return ConnectionStatus(connected=True, account_name="Preview Sandbox")

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        key = f"{campaign.get('id', '')}:{variant.get('id', '')}"
        external_id = "preview_" + hashlib.sha1(key.encode()).hexdigest()[:12]
        return PublishResult(
            external_id=external_id,
            url=f"https://biazmark.local/preview/{external_id}",
            raw={"variant": variant.get("headline", ""), "channel": campaign.get("channel")},
        )

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        """Deterministic-ish synthetic metrics keyed off external_id.

        Gives the optimizer something to chew on without live ads.
        """
        out: list[Metric] = []
        for eid in external_ids:
            seed = int(hashlib.sha1(eid.encode()).hexdigest(), 16) % (2**32)
            rng = random.Random(seed)
            impressions = rng.randint(800, 12000)
            ctr = rng.uniform(0.005, 0.08)
            cvr = rng.uniform(0.005, 0.12)
            clicks = int(impressions * ctr)
            conversions = int(clicks * cvr)
            spend = round(impressions * rng.uniform(0.002, 0.015), 2)
            revenue = round(conversions * rng.uniform(10, 80), 2)
            out.append(
                Metric(
                    external_id=eid,
                    impressions=impressions,
                    clicks=clicks,
                    conversions=conversions,
                    spend=spend,
                    revenue=revenue,
                    engagement=int(clicks * rng.uniform(1.2, 2.5)),
                    raw={"simulated": True},
                )
            )
        return out
