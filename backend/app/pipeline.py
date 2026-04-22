"""The end-to-end marketing pipeline.

Composes: research gathering → Researcher → Strategist → Creator → publish via connector
           → Analyst → Optimizer → Creator (new variants) → publish ↻

This is the only module that knows about *all* the other pieces. Agents and connectors
stay ignorant of each other. The worker calls into this module for the self-improvement
loop, and the API calls into it for one-shot flows (e.g. "give me a strategy now").
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import (
    Analyst,
    ArticleWriter,
    Brief,
    Creator,
    EmailWriter,
    Optimizer,
    Researcher,
    Strategist,
)
from app.config import Tier, get_settings
from app.connectors import registry
from app.db import (
    Business,
    Campaign,
    ConnectorAccount,
    ContentVariant,
    MediaAsset,
    MetricSnapshot,
    OptimizationEvent,
    Research,
    Strategy,
)
from app.llm import LLMClient
from app.logging_config import get_logger
from app.media import media_registry
from app.research import ResearchGatherer
from app.vault import decrypt

log = get_logger(__name__)


class MarketingPipeline:
    """All pipeline operations hang off here. Stateless — each call takes a session."""

    def __init__(self, tier: Tier | None = None):
        self.settings = get_settings()
        self.tier = tier or self.settings.biazmark_tier
        self.llm = LLMClient(tier_override=self.tier)

    # ---------------- research ----------------

    async def run_research(self, session: AsyncSession, business_id: str) -> Research:
        biz = await _get_business(session, business_id)
        brief = _brief_from_business(biz)

        gatherer = ResearchGatherer(depth=self.settings.tier_spec["research_depth"])
        keywords = [kw.strip() for kw in (biz.industry or "").split(",") if kw.strip()]
        signals = await gatherer.gather(
            name=biz.name,
            website=biz.website,
            industry=biz.industry,
            keywords=keywords,
        )
        log.info("research_signals_gathered", business_id=business_id,
                 sources=len(signals.sources), trends=len(signals.trends))

        result = await Researcher(self.llm).run(brief, signals.to_dict())

        record = Research(
            business_id=business_id,
            summary=result.summary,
            competitors=result.competitors,
            trends=result.trends,
            audience_insights=result.audience_insights,
            sources=signals.sources,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        log.info("research_persisted", research_id=record.id)
        return record

    # ---------------- strategy ----------------

    async def run_strategy(
        self,
        session: AsyncSession,
        business_id: str,
        *,
        channels: list[str] | None = None,
        budget_hint: str = "lean",
    ) -> Strategy:
        biz = await _get_business(session, business_id)
        brief = _brief_from_business(biz)
        research = await _latest_research(session, business_id)
        if research is None:
            research = await self.run_research(session, business_id)

        channels = channels or _default_channels(self.tier)

        from app.agents import ResearchResult as RR

        research_dc = RR(
            summary=research.summary,
            competitors=research.competitors or [],
            trends=research.trends or [],
            audience_insights=research.audience_insights or {},
            gaps=(research.raw if hasattr(research, "raw") else {}).get("gaps", []) if False else [],
            risks=[],
        )
        result = await Strategist(self.llm).run(
            brief, research_dc, channels=channels, budget_hint=budget_hint, tier=self.tier
        )

        existing_count = await _count_strategies(session, business_id)
        record = Strategy(
            business_id=business_id,
            version=existing_count + 1,
            positioning=result.positioning,
            value_prop=result.value_prop,
            channels=result.channels,
            messaging_pillars=result.messaging_pillars,
            kpis=result.kpis,
            budget_split=result.budget_split,
            raw=result.raw,
            approved=False,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        log.info("strategy_persisted", strategy_id=record.id, version=record.version)
        return record

    # ---------------- content + publish ----------------

    async def run_create_and_publish(
        self,
        session: AsyncSession,
        business_id: str,
        strategy_id: str,
        *,
        connector_platform: str = "preview",
        generate_media: bool = True,
    ) -> list[Campaign]:
        biz = await _get_business(session, business_id)
        strategy = await _get_strategy(session, strategy_id)
        brief = _brief_from_business(biz)

        from app.agents import StrategyResult as SR

        strategy_dc = SR(
            positioning=strategy.positioning,
            value_prop=strategy.value_prop,
            messaging_pillars=strategy.messaging_pillars or [],
            channels=strategy.channels or [],
            kpis=strategy.kpis or [],
            budget_split=strategy.budget_split or {},
        )
        creator = Creator(self.llm, tier=self.tier)
        article_writer = ArticleWriter(self.llm)
        email_writer = EmailWriter(self.llm)
        campaigns: list[Campaign] = []

        for ch in strategy_dc.channels:
            platform = (ch.get("platform") or connector_platform).lower()
            objective = ch.get("objective", "awareness")

            for pillar in strategy_dc.messaging_pillars[:3]:
                pillar_name = pillar.get("name", "default")
                pillar_angle = pillar.get("angle", "")

                campaign = Campaign(
                    business_id=business_id,
                    strategy_id=strategy_id,
                    name=f"{platform}: {pillar_name}",
                    channel=platform,
                    objective=objective,
                    status="draft",
                )
                session.add(campaign)
                await session.flush()

                # Which content kind does this channel want?
                variants_to_create = await self._create_variants_for_channel(
                    brief, strategy_dc, platform, pillar_name, pillar_angle,
                    objective, creator, article_writer, email_writer,
                    business_id, campaign.id, session,
                )

                for v in variants_to_create:
                    session.add(v)
                await session.flush()

                if generate_media:
                    await self._attach_media(session, variants_to_create, business_id)

                await self._publish_campaign(session, campaign, platform)
                campaigns.append(campaign)

        await session.commit()
        return campaigns

    async def _create_variants_for_channel(
        self,
        brief: Brief,
        strategy_dc,
        platform: str,
        pillar_name: str,
        pillar_angle: str,
        objective: str,
        creator: Creator,
        article_writer: ArticleWriter,
        email_writer: EmailWriter,
        business_id: str,
        campaign_id: str,
        session: AsyncSession,
    ) -> list[ContentVariant]:
        """Route per-channel: blog → article, email → email, rest → social post variants."""
        out: list[ContentVariant] = []
        if platform in ("blog", "seo", "wordpress"):
            article = await article_writer.run(
                brief, strategy_dc,
                pillar=pillar_name, angle=pillar_angle,
                keyword=pillar_name, audience=brief.target_audience,
            )
            out.append(ContentVariant(
                campaign_id=campaign_id,
                kind="article",
                headline=article.title[:500],
                body=article.meta_description,
                long_body=article.body_markdown,
                cta=article.cta[:200],
                visual_prompt=article.hero_image_prompt,
                meta={
                    "slug": article.slug,
                    "outline": article.outline,
                    "keywords": article.keywords,
                    "angle": pillar_angle,
                },
                status="generated",
            ))
        elif platform in ("email", "resend", "sendgrid"):
            email = await email_writer.run(
                brief, strategy_dc,
                segment=brief.target_audience or "general",
                purpose=f"{objective} via {pillar_name}",
            )
            out.append(ContentVariant(
                campaign_id=campaign_id,
                kind="email",
                headline=email.subject[:500],
                body=email.body_plain,
                long_body=email.body_html,
                cta=email.cta_text[:200],
                meta={
                    "preview": email.preview,
                    "cta_url_placeholder": email.cta_url_placeholder,
                    "angle": pillar_angle,
                },
                status="generated",
            ))
        else:
            pack = await creator.run(
                brief, strategy_dc,
                platform=platform, pillar=pillar_name, objective=objective,
            )
            for v in pack.variants:
                out.append(ContentVariant(
                    campaign_id=campaign_id,
                    kind="ad" if objective == "conversion" else "post",
                    headline=v.get("headline", "")[:500],
                    body=v.get("body", ""),
                    cta=v.get("cta", "")[:200],
                    visual_prompt=v.get("visual_prompt", ""),
                    meta={
                        "angle": v.get("angle"),
                        "hashtags": v.get("hashtags", []),
                        "predicted_strength": v.get("predicted_strength"),
                    },
                    status="generated",
                ))
        return out

    async def _attach_media(
        self, session: AsyncSession, variants: list[ContentVariant], business_id: str
    ) -> None:
        """Run each variant's visual_prompt through the best-available media provider."""
        provider = media_registry.pick()
        for v in variants:
            prompt = v.visual_prompt
            if not prompt:
                continue
            try:
                result = await provider.generate(prompt, aspect=_aspect_for(v))
                v.media_url = result.url
                v.media_kind = result.kind
                session.add(MediaAsset(
                    business_id=business_id,
                    variant_id=v.id,
                    kind=result.kind,
                    prompt=prompt,
                    provider=result.provider,
                    url=result.url,
                    local_path=result.local_path,
                    width=result.width,
                    height=result.height,
                    meta=result.meta,
                ))
            except Exception as e:
                log.warning("media_gen_failed", variant_id=v.id, error=str(e))

    async def _publish_campaign(
        self, session: AsyncSession, campaign: Campaign, platform: str
    ) -> None:
        """Publish all un-published variants of a campaign via the chosen connector.

        Credential resolution order:
            1. Per-business ConnectorAccount (OAuth) — preferred
            2. Env-var fallback (set on the connector class)
            3. Preview connector (dry-run) — last resort
        """
        creds = await _credentials_for(session, campaign.business_id, platform)
        try:
            connector = registry.instantiate(platform, credentials=creds)
        except KeyError:
            connector = registry.instantiate("preview")
        status = await connector.connect()
        if not status.connected:
            log.warning("connector_not_connected", platform=platform, error=status.error)
            connector = registry.instantiate("preview")
            await connector.connect()

        result_vars = await session.execute(
            select(ContentVariant).where(
                ContentVariant.campaign_id == campaign.id,
                ContentVariant.status == "generated",
            )
        )
        variants = result_vars.scalars().all()

        campaign_payload = {"id": campaign.id, "channel": campaign.channel,
                            "objective": campaign.objective, "name": campaign.name}
        for v in variants:
            pr = await connector.publish(
                {
                    "id": v.id,
                    "kind": v.kind,
                    "headline": v.headline,
                    "body": v.body,
                    "long_body": v.long_body,
                    "cta": v.cta,
                    "media_url": v.media_url,
                    "media_kind": v.media_kind,
                    "hashtags": (v.meta or {}).get("hashtags", []),
                    "meta": v.meta or {},
                },
                campaign_payload,
            )
            v.external_id = pr.external_id
            v.external_url = pr.url
            v.status = "live" if pr.external_id else "rejected"

        campaign.status = "live"

    # ---------------- analyse + optimize (self-improvement loop) ----------------

    async def run_analyse_and_optimize(
        self, session: AsyncSession, campaign_id: str
    ) -> OptimizationEvent | None:
        campaign = await _get_campaign(session, campaign_id)
        strategy = await _get_strategy(session, campaign.strategy_id)

        # 1. pull fresh metrics
        creds = await _credentials_for(session, campaign.business_id, campaign.channel)
        try:
            connector = registry.instantiate(campaign.channel, credentials=creds)
            status = await connector.connect()
            if not status.connected:
                connector = registry.instantiate("preview")
                await connector.connect()
        except KeyError:
            connector = registry.instantiate("preview")
            await connector.connect()

        variants_res = await session.execute(
            select(ContentVariant).where(ContentVariant.campaign_id == campaign_id)
        )
        variants = variants_res.scalars().all()
        external_ids = [v.external_id for v in variants if v.external_id]
        if not external_ids:
            log.info("no_external_ids_skipping", campaign_id=campaign_id)
            return None

        metrics = await connector.fetch_metrics(external_ids)
        by_eid = {m.external_id: m for m in metrics}
        metric_payload: list[dict[str, Any]] = []
        for v in variants:
            m = by_eid.get(v.external_id)
            if not m:
                continue
            session.add(
                MetricSnapshot(
                    campaign_id=campaign_id,
                    variant_id=v.id,
                    impressions=m.impressions,
                    clicks=m.clicks,
                    conversions=m.conversions,
                    spend=m.spend,
                    revenue=m.revenue,
                    engagement=m.engagement,
                    raw=m.raw,
                )
            )
            metric_payload.append(
                {
                    "variant_id": v.id,
                    "headline": v.headline,
                    "impressions": m.impressions,
                    "clicks": m.clicks,
                    "conversions": m.conversions,
                    "spend": m.spend,
                    "revenue": m.revenue,
                    "ctr": (m.clicks / m.impressions) if m.impressions else 0,
                    "cvr": (m.conversions / m.clicks) if m.clicks else 0,
                    "roas": (m.revenue / m.spend) if m.spend else 0,
                }
            )

        # 2. analyst
        analysis = await Analyst(self.llm).run(strategy.kpis or [], metric_payload)

        # 3. optimizer
        from app.agents import StrategyResult as SR

        strategy_dc = SR(
            positioning=strategy.positioning,
            value_prop=strategy.value_prop,
            messaging_pillars=strategy.messaging_pillars or [],
            channels=strategy.channels or [],
            kpis=strategy.kpis or [],
            budget_split=strategy.budget_split or {},
        )
        plan = await Optimizer(self.llm).run(strategy_dc, analysis)

        # 4. apply changes
        applied: list[dict[str, Any]] = []
        for change in plan.changes:
            applied.append(await self._apply_change(session, campaign, change))

        event = OptimizationEvent(
            business_id=campaign.business_id,
            campaign_id=campaign_id,
            kind="cycle",
            reason=analysis.headline,
            payload={
                "analysis": asdict(analysis),
                "plan": asdict(plan),
                "applied": applied,
                "metrics_sample": metric_payload[:10],
            },
        )
        session.add(event)
        await session.commit()
        log.info("optimization_cycle_done", campaign_id=campaign_id, changes=len(applied))
        return event

    async def _apply_change(
        self, session: AsyncSession, campaign: Campaign, change: dict[str, Any]
    ) -> dict[str, Any]:
        kind = (change.get("kind") or "").lower()
        target = change.get("target", "")
        details = change.get("details", "")
        if kind == "kill_variant":
            v = await session.get(ContentVariant, target)
            if v:
                v.status = "killed"
                return {"applied": True, "kind": kind, "target": target}
        elif kind == "scale_variant":
            v = await session.get(ContentVariant, target)
            if v:
                v.score = (v.score or 0) + 1.0
                return {"applied": True, "kind": kind, "target": target}
        elif kind == "reframe_pillar":
            return {"applied": False, "kind": kind, "target": target, "reason": "reframe logged; new variants in next creator pass"}
        return {"applied": False, "kind": kind, "target": target, "details": details}


# ---------------- helpers ----------------


def _brief_from_business(b: Business) -> Brief:
    return Brief(
        name=b.name,
        description=b.description,
        website=b.website,
        industry=b.industry,
        target_audience=b.target_audience,
        goals=b.goals,
        extra=b.brief_raw or {},
    )


def _default_channels(tier: Tier) -> list[str]:
    if tier == Tier.FREE:
        return ["preview"]
    if tier == Tier.BASIC:
        return ["meta"]
    if tier == Tier.PRO:
        return ["meta", "google_ads", "linkedin", "x", "tiktok"]
    return ["meta", "google_ads", "linkedin", "x", "tiktok", "email", "seo"]


async def _get_business(session: AsyncSession, business_id: str) -> Business:
    biz = await session.get(Business, business_id)
    if biz is None:
        raise LookupError(f"Business {business_id} not found")
    return biz


async def _get_strategy(session: AsyncSession, strategy_id: str) -> Strategy:
    s = await session.get(Strategy, strategy_id)
    if s is None:
        raise LookupError(f"Strategy {strategy_id} not found")
    return s


async def _get_campaign(session: AsyncSession, campaign_id: str) -> Campaign:
    c = await session.get(Campaign, campaign_id)
    if c is None:
        raise LookupError(f"Campaign {campaign_id} not found")
    return c


async def _latest_research(session: AsyncSession, business_id: str) -> Research | None:
    res = await session.execute(
        select(Research)
        .where(Research.business_id == business_id)
        .order_by(Research.created_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def _count_strategies(session: AsyncSession, business_id: str) -> int:
    from sqlalchemy import func as sqlfunc

    res = await session.execute(
        select(sqlfunc.count(Strategy.id)).where(Strategy.business_id == business_id)
    )
    return int(res.scalar_one() or 0)


def _aspect_for(v: ContentVariant) -> str:
    """Pick an aspect ratio based on content kind + channel heuristics."""
    if v.kind == "article":
        return "16:9"
    meta = v.meta or {}
    angle = (meta.get("angle") or "").lower()
    if "story" in angle or "reel" in angle:
        return "9:16"
    return "1:1"


async def _credentials_for(
    session: AsyncSession, business_id: str, platform: str
) -> dict[str, Any]:
    """Resolve credentials for (business, platform) — DB first, env second, empty last."""
    res = await session.execute(
        select(ConnectorAccount).where(
            ConnectorAccount.business_id == business_id,
            ConnectorAccount.platform == platform,
        )
    )
    acc = res.scalar_one_or_none()
    if acc and acc.credentials_enc:
        creds = decrypt(acc.credentials_enc)
        creds["_account_meta"] = acc.account_meta or {}
        return creds
    return {}
