"""End-to-end pipeline test with in-memory SQLite + mocked LLM.

Verifies the full flow: research → strategy → publish → optimize.
No external services required — guarantees the loop closes on any CI host.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("BIAZMARK_TIER", "free")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    # Reset the settings cache so env changes take effect.
    from app import config as _cfg

    _cfg.get_settings.cache_clear()
    yield
    _cfg.get_settings.cache_clear()


@pytest.fixture
def mocked_llm(monkeypatch):
    from app import llm as _llm

    async def fake(self, system, user, schema_hint="", max_tokens=2048):
        if "Researcher" in system or "market snapshot" in system.lower():
            return {
                "summary": "Market snapshot.",
                "competitors": [{"name": "Rival", "positioning": "cheap"}],
                "trends": [{"label": "ai tooling", "direction": "rising"}],
                "audience_insights": {"primary_segments": ["devs"]},
                "gaps": [],
                "risks": [],
            }
        if "Strategist" in system:
            return {
                "positioning": "X for Y.",
                "value_prop": "Does the thing.",
                "messaging_pillars": [
                    {"name": "Speed", "angle": "fast", "proof_points": ["p1"]},
                ],
                "channels": [{"platform": "preview", "objective": "awareness", "why": "test"}],
                "kpis": [{"name": "CTR", "target": "2%", "measurement": "reported"}],
                "budget_split": {"preview": 100},
                "experiments": [],
            }
        if "Article Writer" in system:
            return {
                "title": "test", "slug": "test", "meta_description": "d",
                "hero_image_prompt": "p", "outline": [], "body_markdown": "# t",
                "cta": "go", "keywords": [],
            }
        if "Email Writer" in system:
            return {
                "subject": "s", "preview": "p", "body_plain": "t",
                "body_html": "<p>t</p>", "cta_text": "go", "cta_url_placeholder": "",
            }
        if "Creator" in system or "variants" in user.lower():
            return {
                "variants": [
                    {"angle": "proof", "headline": "h1", "body": "b1", "cta": "c1",
                     "visual_prompt": "vp1", "hashtags": ["t"], "predicted_strength": "7"},
                    {"angle": "story", "headline": "h2", "body": "b2", "cta": "c2",
                     "visual_prompt": "vp2", "hashtags": ["t"], "predicted_strength": "8"},
                ]
            }
        if "Analyst" in system:
            return {"headline": "Looks fine.", "winners": [], "losers": [],
                    "surprises": [], "recommended_actions": []}
        if "Optimizer" in system:
            return {"changes": [], "new_variant_briefs": [], "next_review_hours": 24}
        return {}

    monkeypatch.setattr(_llm.LLMClient, "complete_json", fake)


async def test_pipeline_end_to_end(mocked_llm):
    from app.config import Tier
    from app.db import Business, init_db, session_factory
    from app.pipeline import MarketingPipeline

    await init_db()

    async with session_factory()() as s:
        biz = Business(name="TestCo", description="smoke test", industry="tech", tier=Tier.FREE)
        s.add(biz)
        await s.commit()
        business_id = biz.id

    pipe = MarketingPipeline(tier=Tier.FREE)

    async with session_factory()() as s:
        research = await pipe.run_research(s, business_id)
    assert research.summary == "Market snapshot."

    async with session_factory()() as s:
        strategy = await pipe.run_strategy(s, business_id, channels=["preview"])
    assert strategy.positioning == "X for Y."
    assert strategy.version == 1
    strategy_id = strategy.id

    async with session_factory()() as s:
        campaigns = await pipe.run_create_and_publish(
            s, business_id, strategy_id, connector_platform="preview"
        )
    assert len(campaigns) >= 1
    assert all(c.status == "live" for c in campaigns)
    camp_id = campaigns[0].id

    async with session_factory()() as s:
        event = await pipe.run_analyse_and_optimize(s, camp_id)
    assert event is not None
    assert "applied" in event.payload


async def test_pipeline_multi_kind(mocked_llm):
    """Blog + email + social in a single strategy → 3 kinds of variants."""
    from sqlalchemy import select

    from app.config import Tier
    from app.db import Business, ContentVariant, init_db, session_factory
    from app.pipeline import MarketingPipeline

    await init_db()
    async with session_factory()() as s:
        biz = Business(name="Multi", description="test", industry="tech", tier=Tier.FREE)
        s.add(biz)
        await s.commit()
        business_id = biz.id

    pipe = MarketingPipeline(tier=Tier.FREE)
    async with session_factory()() as s:
        await pipe.run_research(s, business_id)
    async with session_factory()() as s:
        # Strategist mock returns only preview — override channel list directly for this test.
        from app import llm as _llm
        orig = _llm.LLMClient.complete_json

        async def multi_channel(self, system, user, schema_hint="", max_tokens=2048):
            data = await orig(self, system, user, schema_hint=schema_hint, max_tokens=max_tokens)
            if "Strategist" in system:
                data["channels"] = [
                    {"platform": "preview", "objective": "awareness"},
                    {"platform": "blog", "objective": "consideration"},
                    {"platform": "email", "objective": "retention"},
                ]
            return data

        _llm.LLMClient.complete_json = multi_channel
        strategy = await pipe.run_strategy(s, business_id, channels=["preview", "blog", "email"])
        sid = strategy.id

    async with session_factory()() as s:
        campaigns = await pipe.run_create_and_publish(
            s, business_id, sid, connector_platform="preview"
        )
    assert len(campaigns) == 3
    channels = {c.channel for c in campaigns}
    assert channels == {"preview", "blog", "email"}

    async with session_factory()() as s:
        res = await s.execute(select(ContentVariant))
        variants = res.scalars().all()
    kinds = {v.kind for v in variants}
    assert {"post", "article", "email"} <= kinds
