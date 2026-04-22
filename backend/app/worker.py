"""Background worker — self-improvement loop.

Uses arq (async Redis queue). Two modes:

1. **Cron** — every N seconds (per tier), every live campaign runs analyse+optimize.
2. **Ad-hoc jobs** — API can enqueue specific tasks (e.g. "optimize this campaign now").

Stopping/starting the worker is idempotent; the loop picks up wherever it left off.
"""
from __future__ import annotations

from datetime import datetime

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select

from app.config import TierSpec, get_settings
from app.db import Business, Campaign, session_factory
from app.logging_config import get_logger, setup_logging
from app.pipeline import MarketingPipeline

setup_logging()
log = get_logger(__name__)


async def optimize_campaign_task(ctx: dict, campaign_id: str) -> dict:
    """Run one analyse+optimize cycle on a single campaign."""
    async with session_factory()() as session:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            log.warning("optimize_skipped_no_campaign", campaign_id=campaign_id)
            return {"ok": False, "reason": "not_found"}
        biz = await session.get(Business, campaign.business_id)
        pipe = MarketingPipeline(tier=biz.tier if biz else None)
        event = await pipe.run_analyse_and_optimize(session, campaign_id)
        return {"ok": True, "event_id": event.id if event else None}


async def full_research_task(ctx: dict, business_id: str) -> dict:
    async with session_factory()() as session:
        biz = await session.get(Business, business_id)
        if biz is None:
            return {"ok": False, "reason": "not_found"}
        pipe = MarketingPipeline(tier=biz.tier)
        record = await pipe.run_research(session, business_id)
        return {"ok": True, "research_id": record.id}


async def tick_all_live_campaigns(ctx: dict) -> dict:
    """Cron tick: walk every live campaign and optimize it."""
    touched = 0
    async with session_factory()() as session:
        res = await session.execute(select(Campaign).where(Campaign.status == "live"))
        campaigns = res.scalars().all()
    # Use a fresh session per campaign to isolate failures.
    for c in campaigns:
        async with session_factory()() as s:
            try:
                biz = await s.get(Business, c.business_id)
                pipe = MarketingPipeline(tier=biz.tier if biz else None)
                await pipe.run_analyse_and_optimize(s, c.id)
                touched += 1
            except Exception as e:
                log.warning("tick_campaign_failed", campaign_id=c.id, error=str(e))
    log.info("tick_done", touched=touched, at=datetime.utcnow().isoformat())
    return {"touched": touched}


def _default_cron_minutes() -> int:
    """Derive cron cadence from the configured tier's loop interval."""
    spec = TierSpec.for_tier(get_settings().biazmark_tier)
    secs = spec.get("loop_interval_seconds")
    if not secs:
        return 60 * 24  # daily — safe default for manual tiers
    return max(1, int(secs // 60))


class WorkerSettings:
    """arq WorkerSettings — `arq app.worker.WorkerSettings` runs this."""

    functions = [optimize_campaign_task, full_research_task, tick_all_live_campaigns]
    cron_jobs = [
        cron(
            tick_all_live_campaigns,
            minute={i for i in range(0, 60, max(1, _default_cron_minutes() % 60 or 15))},
            hour=None,
            run_at_startup=False,
        ),
    ]

    @classmethod
    @property
    def redis_settings(cls) -> RedisSettings:  # type: ignore[misc]
        url = get_settings().redis_url
        # arq takes RedisSettings; parse the URL roughly.
        from urllib.parse import urlparse

        u = urlparse(url)
        return RedisSettings(
            host=u.hostname or "localhost",
            port=u.port or 6379,
            database=int((u.path or "/0").lstrip("/") or 0),
            password=u.password or None,
        )
