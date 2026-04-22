"""The 5 autonomous agents that drive the marketing system.

Each agent is a pure async function that takes structured input, calls the LLM via
`LLMClient`, and returns structured output. No agent writes to the DB directly — the
API / worker layer is responsible for persistence. This keeps agents testable, replayable,
and composable.

Flow:

    researcher → strategist → creator → (publish via connector) → analyst → optimizer → creator ↻

The optimizer feeds back into the creator, closing the self-improvement loop.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from app.config import Tier, TierSpec
from app.llm import LLMClient
from app.logging_config import get_logger
from app.prompts import (
    ANALYST_SYSTEM,
    ANALYST_USER_TEMPLATE,
    ARTICLE_SYSTEM,
    ARTICLE_USER_TEMPLATE,
    CREATOR_SYSTEM,
    CREATOR_USER_TEMPLATE,
    EMAIL_SYSTEM,
    EMAIL_USER_TEMPLATE,
    OPTIMIZER_SYSTEM,
    OPTIMIZER_USER_TEMPLATE,
    RESEARCHER_SYSTEM,
    RESEARCHER_USER_TEMPLATE,
    STRATEGIST_SYSTEM,
    STRATEGIST_USER_TEMPLATE,
)

log = get_logger(__name__)


# ========== data contracts ==========


@dataclass
class Brief:
    name: str
    description: str
    website: str = ""
    industry: str = ""
    target_audience: str = ""
    goals: str = ""
    language: str = "auto"  # auto|he|en|...
    extra: dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


@dataclass
class ResearchResult:
    summary: str
    competitors: list[dict[str, Any]]
    trends: list[dict[str, Any]]
    audience_insights: dict[str, Any]
    gaps: list[str]
    risks: list[str]
    sources: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyResult:
    positioning: str
    value_prop: str
    messaging_pillars: list[dict[str, Any]]
    channels: list[dict[str, Any]]
    kpis: list[dict[str, Any]]
    budget_split: dict[str, Any]
    experiments: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentPack:
    platform: str
    pillar: str
    objective: str
    variants: list[dict[str, Any]]


@dataclass
class AnalysisResult:
    headline: str
    winners: list[dict[str, Any]]
    losers: list[dict[str, Any]]
    surprises: list[str]
    recommended_actions: list[dict[str, Any]]


@dataclass
class OptimizationPlan:
    changes: list[dict[str, Any]]
    new_variant_briefs: list[dict[str, Any]]
    next_review_hours: int = 24


@dataclass
class Article:
    title: str
    slug: str
    meta_description: str
    hero_image_prompt: str
    outline: list[str]
    body_markdown: str
    cta: str
    keywords: list[str]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailContent:
    subject: str
    preview: str
    body_plain: str
    body_html: str
    cta_text: str
    cta_url_placeholder: str
    raw: dict[str, Any] = field(default_factory=dict)


# ========== agents ==========


class Researcher:
    """Synthesises a market snapshot from the brief + raw signals (web/trends/etc.)."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, brief: Brief, signals: dict[str, Any]) -> ResearchResult:
        user = RESEARCHER_USER_TEMPLATE.format(
            brief=brief.to_prompt(),
            signals=json.dumps(signals, ensure_ascii=False, indent=2)[:6000],
        )
        data = await self.llm.complete_json(RESEARCHER_SYSTEM, user, max_tokens=2500)
        return ResearchResult(
            summary=data.get("summary", ""),
            competitors=data.get("competitors", []),
            trends=data.get("trends", []),
            audience_insights=data.get("audience_insights", {}),
            gaps=data.get("gaps", []),
            risks=data.get("risks", []),
            sources=signals.get("_sources", []),
            raw=data,
        )


class Strategist:
    """Turns brief + research into an executable strategy."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(
        self,
        brief: Brief,
        research: ResearchResult,
        *,
        channels: list[str],
        budget_hint: str = "lean",
        tier: Tier = Tier.BASIC,
    ) -> StrategyResult:
        user = STRATEGIST_USER_TEMPLATE.format(
            brief=brief.to_prompt(),
            research=json.dumps(asdict(research), ensure_ascii=False, indent=2)[:6000],
            tier=tier.value,
            channels=", ".join(channels),
            budget_hint=budget_hint,
        )
        data = await self.llm.complete_json(STRATEGIST_SYSTEM, user, max_tokens=3000)
        return StrategyResult(
            positioning=data.get("positioning", ""),
            value_prop=data.get("value_prop", ""),
            messaging_pillars=data.get("messaging_pillars", []),
            channels=data.get("channels", []),
            kpis=data.get("kpis", []),
            budget_split=data.get("budget_split", {}),
            experiments=data.get("experiments", []),
            raw=data,
        )


class Creator:
    """Generates N content variants for a single (platform, pillar, objective)."""

    def __init__(self, llm: LLMClient, tier: Tier):
        self.llm = llm
        self.n_variants = TierSpec.for_tier(tier)["max_content_variants"]

    async def run(
        self,
        brief: Brief,
        strategy: StrategyResult,
        *,
        platform: str,
        pillar: str,
        objective: str,
    ) -> ContentPack:
        system = CREATOR_SYSTEM.format(n_variants=self.n_variants)
        user = CREATOR_USER_TEMPLATE.format(
            brief=brief.to_prompt(),
            strategy=json.dumps(asdict(strategy), ensure_ascii=False, indent=2)[:5000],
            platform=platform,
            pillar=pillar,
            objective=objective,
        )
        data = await self.llm.complete_json(system, user, max_tokens=3500)
        return ContentPack(
            platform=platform,
            pillar=pillar,
            objective=objective,
            variants=data.get("variants", []),
        )


class Analyst:
    """Reads back metrics per variant → identifies winners/losers/actions."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(
        self,
        kpis: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
    ) -> AnalysisResult:
        user = ANALYST_USER_TEMPLATE.format(
            kpis=json.dumps(kpis, ensure_ascii=False, indent=2),
            metrics=json.dumps(metrics, ensure_ascii=False, indent=2)[:6000],
        )
        data = await self.llm.complete_json(ANALYST_SYSTEM, user, max_tokens=2500)
        return AnalysisResult(
            headline=data.get("headline", ""),
            winners=data.get("winners", []),
            losers=data.get("losers", []),
            surprises=data.get("surprises", []),
            recommended_actions=data.get("recommended_actions", []),
        )


class Optimizer:
    """Turns analysis into a concrete change set that the worker will execute."""

    def __init__(self, llm: LLMClient, max_changes: int = 5):
        self.llm = llm
        self.max_changes = max_changes

    async def run(
        self, strategy: StrategyResult, analysis: AnalysisResult
    ) -> OptimizationPlan:
        system = OPTIMIZER_SYSTEM.format(max_changes=self.max_changes)
        user = OPTIMIZER_USER_TEMPLATE.format(
            strategy=json.dumps(asdict(strategy), ensure_ascii=False, indent=2)[:5000],
            analysis=json.dumps(asdict(analysis), ensure_ascii=False, indent=2)[:4000],
        )
        data = await self.llm.complete_json(system, user, max_tokens=2000)
        return OptimizationPlan(
            changes=data.get("changes", []),
            new_variant_briefs=data.get("new_variant_briefs", []),
            next_review_hours=int(data.get("next_review_hours", 24) or 24),
        )


class ArticleWriter:
    """Long-form article generator — SEO-aware, markdown output."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(
        self,
        brief: Brief,
        strategy: StrategyResult,
        *,
        pillar: str,
        angle: str,
        keyword: str,
        audience: str = "",
    ) -> Article:
        user = ARTICLE_USER_TEMPLATE.format(
            brief=brief.to_prompt(),
            strategy=json.dumps(asdict(strategy), ensure_ascii=False, indent=2)[:4000],
            pillar=pillar,
            angle=angle,
            keyword=keyword,
            audience=audience or brief.target_audience,
        )
        data = await self.llm.complete_json(ARTICLE_SYSTEM, user, max_tokens=6000)
        return Article(
            title=data.get("title", ""),
            slug=data.get("slug", ""),
            meta_description=data.get("meta_description", ""),
            hero_image_prompt=data.get("hero_image_prompt", ""),
            outline=data.get("outline", []),
            body_markdown=data.get("body_markdown", ""),
            cta=data.get("cta", ""),
            keywords=data.get("keywords", []),
            raw=data,
        )


class EmailWriter:
    """Email broadcast writer."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(
        self,
        brief: Brief,
        strategy: StrategyResult,
        *,
        segment: str,
        purpose: str,
    ) -> EmailContent:
        user = EMAIL_USER_TEMPLATE.format(
            brief=brief.to_prompt(),
            strategy=json.dumps(asdict(strategy), ensure_ascii=False, indent=2)[:3500],
            segment=segment,
            purpose=purpose,
        )
        data = await self.llm.complete_json(EMAIL_SYSTEM, user, max_tokens=2000)
        return EmailContent(
            subject=data.get("subject", ""),
            preview=data.get("preview", ""),
            body_plain=data.get("body_plain", ""),
            body_html=data.get("body_html", ""),
            cta_text=data.get("cta_text", ""),
            cta_url_placeholder=data.get("cta_url_placeholder", ""),
            raw=data,
        )
