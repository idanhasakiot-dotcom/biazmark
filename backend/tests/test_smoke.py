"""Smoke tests — verify the app boots, schemas load, connectors auto-register.

These are intentionally dependency-free (no DB, no LLM) so they run everywhere.
"""
from __future__ import annotations


def test_app_imports():
    from app.main import app

    assert app.title == "Biazmark"


def test_connector_registry_populated():
    import app.connectors  # noqa: F401
    from app.connectors.base import registry

    platforms = {c["platform"] for c in registry.available()}
    assert {"preview", "meta", "google_ads", "linkedin", "tiktok", "x"} <= platforms


def test_tier_specs_complete():
    from app.config import Tier, TierSpec

    required = {
        "llm_provider",
        "llm_model",
        "research_depth",
        "max_connectors",
        "loop_interval_seconds",
        "autonomous_agents",
        "max_content_variants",
    }
    for t in Tier:
        assert required <= set(TierSpec.for_tier(t).keys())


def test_prompts_format():
    from app.prompts import (
        CREATOR_USER_TEMPLATE,
        RESEARCHER_USER_TEMPLATE,
        STRATEGIST_USER_TEMPLATE,
    )

    assert "{brief}" in RESEARCHER_USER_TEMPLATE
    assert "{brief}" in STRATEGIST_USER_TEMPLATE
    assert "{brief}" in CREATOR_USER_TEMPLATE
