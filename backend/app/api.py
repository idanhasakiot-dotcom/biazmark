"""REST API — thin FastAPI layer on top of the pipeline.

All business logic lives in `pipeline.py` and `agents.py`. This module is glue:
request validation → pipeline call → response shaping + optional background kick-off.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import TierSpec, get_settings
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
    get_session,
)
from app.media import media_registry
from app.oauth import oauth_registry
from app.oauth.manager import OAuthManager
from app.pipeline import MarketingPipeline, _credentials_for
from app.schemas import (
    BusinessCreate,
    BusinessOut,
    CampaignOut,
    ConnectorAccountOut,
    ConnectorOut,
    ConnectorStatusOut,
    ContentVariantOut,
    MediaAssetOut,
    MetricOut,
    OAuthStartOut,
    OptimizationEventOut,
    PublishRequest,
    ResearchOut,
    StrategyOut,
    StrategyRequest,
    TierOut,
)

router = APIRouter(prefix="/api", tags=["biazmark"])


# ---------------- meta ----------------


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok"}


@router.get("/tier", response_model=TierOut)
async def current_tier() -> TierOut:
    s = get_settings()
    spec = TierSpec.for_tier(s.biazmark_tier)
    return TierOut(tier=s.biazmark_tier, **spec)


@router.get("/connectors", response_model=list[ConnectorOut])
async def list_connectors() -> list[ConnectorOut]:
    return [ConnectorOut(**c) for c in registry.available()]


@router.get("/media/providers")
async def list_media_providers() -> list[dict[str, Any]]:
    return media_registry.all()


# ---------------- oauth ----------------


@router.get("/oauth/platforms")
async def oauth_platforms() -> list[dict[str, Any]]:
    """Which OAuth platforms have client credentials set up in settings."""
    return OAuthManager().platforms_configured()


@router.post("/businesses/{business_id}/oauth/{platform}/start", response_model=OAuthStartOut)
async def oauth_start(
    business_id: str,
    platform: str,
    session: AsyncSession = Depends(get_session),
) -> OAuthStartOut:
    biz = await session.get(Business, business_id)
    if biz is None:
        raise HTTPException(404, "Business not found")
    try:
        result = await OAuthManager().start(session, business_id, platform)
    except LookupError as e:
        raise HTTPException(400, str(e)) from e
    return OAuthStartOut(authorise_url=result.authorise_url, state=result.state)


@router.get("/oauth/callback/{platform}")
async def oauth_callback(
    platform: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """OAuth redirect endpoint. Exchanges the `code` and redirects to the dashboard."""
    state = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    error = request.query_params.get("error", "")
    if error:
        raise HTTPException(400, f"oauth error: {error}")
    if not (state and code):
        raise HTTPException(400, "missing state/code")
    try:
        acc = await OAuthManager().finish(session, state, code)
    except LookupError as e:
        raise HTTPException(400, str(e)) from e
    frontend = get_settings().cors_list[0] if get_settings().cors_list else "/"
    return RedirectResponse(f"{frontend}/dashboard/{acc.business_id}?connected={platform}")


@router.get("/businesses/{business_id}/connections", response_model=list[ConnectorAccountOut])
async def list_connections(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> list[ConnectorAccountOut]:
    res = await session.execute(
        select(ConnectorAccount).where(ConnectorAccount.business_id == business_id)
    )
    return [ConnectorAccountOut.model_validate(a) for a in res.scalars().all()]


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str, session: AsyncSession = Depends(get_session)
) -> None:
    acc = await session.get(ConnectorAccount, connection_id)
    if acc is None:
        raise HTTPException(404, "connection not found")
    await session.delete(acc)
    await session.commit()


@router.get("/businesses/{business_id}/connector-status", response_model=list[ConnectorStatusOut])
async def connector_status(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> list[ConnectorStatusOut]:
    """One-shot health + OAuth status per platform for this business."""
    manager = OAuthManager()
    oauth_conf = {p["platform"]: p["configured"] for p in manager.platforms_configured()}
    res = await session.execute(
        select(ConnectorAccount).where(ConnectorAccount.business_id == business_id)
    )
    by_platform = {a.platform: a for a in res.scalars().all()}

    out: list[ConnectorStatusOut] = []
    for c in registry.available():
        p = c["platform"]
        acc = by_platform.get(p)
        connected = False
        account_name = ""
        account_meta: dict[str, Any] = {}
        if acc:
            creds = await _credentials_for(session, business_id, p)
            try:
                inst = registry.instantiate(p, credentials=creds)
                status = await inst.connect()
                connected = status.connected
                account_name = status.account_name or acc.display_name
                account_meta = acc.account_meta or {}
            except Exception:
                connected = False
        out.append(ConnectorStatusOut(
            platform=p,
            display_name=c["display_name"],
            oauth_supported=p in oauth_registry.platforms(),
            oauth_configured=oauth_conf.get(p, False),
            connected=connected,
            account_name=account_name,
            account_meta=account_meta,
        ))
    return out


# ---------------- businesses ----------------


@router.post("/businesses", response_model=BusinessOut, status_code=201)
async def create_business(
    payload: BusinessCreate,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> BusinessOut:
    biz = Business(**payload.model_dump())
    session.add(biz)
    await session.commit()
    await session.refresh(biz)
    # Kick off research in background so the UI doesn't block.
    background.add_task(_background_research, biz.id, biz.tier)
    return BusinessOut.model_validate(biz)


@router.get("/businesses", response_model=list[BusinessOut])
async def list_businesses(session: AsyncSession = Depends(get_session)) -> list[BusinessOut]:
    res = await session.execute(select(Business).order_by(Business.created_at.desc()))
    return [BusinessOut.model_validate(b) for b in res.scalars().all()]


@router.get("/businesses/{business_id}", response_model=BusinessOut)
async def get_business(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> BusinessOut:
    biz = await session.get(Business, business_id)
    if biz is None:
        raise HTTPException(404, "Business not found")
    return BusinessOut.model_validate(biz)


# ---------------- research ----------------


@router.post("/businesses/{business_id}/research", response_model=ResearchOut)
async def run_research(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> ResearchOut:
    biz = await session.get(Business, business_id)
    if biz is None:
        raise HTTPException(404, "Business not found")
    pipe = MarketingPipeline(tier=biz.tier)
    record = await pipe.run_research(session, business_id)
    return ResearchOut.model_validate(record)


@router.get("/businesses/{business_id}/research", response_model=list[ResearchOut])
async def list_research(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> list[ResearchOut]:
    res = await session.execute(
        select(Research)
        .where(Research.business_id == business_id)
        .order_by(Research.created_at.desc())
    )
    return [ResearchOut.model_validate(r) for r in res.scalars().all()]


# ---------------- strategy ----------------


@router.post("/businesses/{business_id}/strategies", response_model=StrategyOut)
async def run_strategy(
    business_id: str,
    payload: StrategyRequest,
    session: AsyncSession = Depends(get_session),
) -> StrategyOut:
    biz = await session.get(Business, business_id)
    if biz is None:
        raise HTTPException(404, "Business not found")
    pipe = MarketingPipeline(tier=biz.tier)
    strategy = await pipe.run_strategy(
        session, business_id, channels=payload.channels, budget_hint=payload.budget_hint
    )
    return StrategyOut.model_validate(strategy)


@router.get("/businesses/{business_id}/strategies", response_model=list[StrategyOut])
async def list_strategies(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> list[StrategyOut]:
    res = await session.execute(
        select(Strategy)
        .where(Strategy.business_id == business_id)
        .order_by(Strategy.version.desc())
    )
    return [StrategyOut.model_validate(s) for s in res.scalars().all()]


@router.post("/strategies/{strategy_id}/approve", response_model=StrategyOut)
async def approve_strategy(
    strategy_id: str, session: AsyncSession = Depends(get_session)
) -> StrategyOut:
    s = await session.get(Strategy, strategy_id)
    if s is None:
        raise HTTPException(404, "Strategy not found")
    s.approved = True
    await session.commit()
    await session.refresh(s)
    return StrategyOut.model_validate(s)


# ---------------- campaigns + variants ----------------


@router.post("/strategies/{strategy_id}/publish", response_model=list[CampaignOut])
async def publish_strategy(
    strategy_id: str,
    payload: PublishRequest,
    session: AsyncSession = Depends(get_session),
) -> list[CampaignOut]:
    s = await session.get(Strategy, strategy_id)
    if s is None:
        raise HTTPException(404, "Strategy not found")
    pipe = MarketingPipeline()
    campaigns = await pipe.run_create_and_publish(
        session, s.business_id, strategy_id, connector_platform=payload.connector
    )
    return [CampaignOut.model_validate(c) for c in campaigns]


@router.get("/businesses/{business_id}/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> list[CampaignOut]:
    res = await session.execute(
        select(Campaign)
        .where(Campaign.business_id == business_id)
        .order_by(Campaign.created_at.desc())
    )
    return [CampaignOut.model_validate(c) for c in res.scalars().all()]


@router.get("/campaigns/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: str, session: AsyncSession = Depends(get_session)
) -> CampaignOut:
    c = await session.get(Campaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    return CampaignOut.model_validate(c)


@router.get("/campaigns/{campaign_id}/variants", response_model=list[ContentVariantOut])
async def list_variants(
    campaign_id: str, session: AsyncSession = Depends(get_session)
) -> list[ContentVariantOut]:
    res = await session.execute(
        select(ContentVariant)
        .where(ContentVariant.campaign_id == campaign_id)
        .order_by(ContentVariant.created_at.asc())
    )
    return [ContentVariantOut.model_validate(v) for v in res.scalars().all()]


@router.get("/campaigns/{campaign_id}/metrics", response_model=list[MetricOut])
async def list_metrics(
    campaign_id: str, session: AsyncSession = Depends(get_session)
) -> list[MetricOut]:
    res = await session.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.campaign_id == campaign_id)
        .order_by(MetricSnapshot.captured_at.desc())
    )
    return [MetricOut.model_validate(m) for m in res.scalars().all()]


@router.post("/campaigns/{campaign_id}/optimize", response_model=OptimizationEventOut | None)
async def optimize_campaign(
    campaign_id: str, session: AsyncSession = Depends(get_session)
) -> OptimizationEventOut | None:
    c = await session.get(Campaign, campaign_id)
    if c is None:
        raise HTTPException(404, "Campaign not found")
    pipe = MarketingPipeline()
    event = await pipe.run_analyse_and_optimize(session, campaign_id)
    return OptimizationEventOut.model_validate(event) if event else None


@router.get("/businesses/{business_id}/optimizations", response_model=list[OptimizationEventOut])
async def list_optimizations(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> list[OptimizationEventOut]:
    res = await session.execute(
        select(OptimizationEvent)
        .where(OptimizationEvent.business_id == business_id)
        .order_by(OptimizationEvent.created_at.desc())
    )
    return [OptimizationEventOut.model_validate(e) for e in res.scalars().all()]


@router.get("/businesses/{business_id}/content", response_model=list[ContentVariantOut])
async def list_business_content(
    business_id: str,
    kind: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ContentVariantOut]:
    """All content variants across all campaigns for a business, optionally filtered by kind."""
    q = (
        select(ContentVariant)
        .join(Campaign, Campaign.id == ContentVariant.campaign_id)
        .where(Campaign.business_id == business_id)
        .order_by(ContentVariant.created_at.desc())
    )
    if kind:
        q = q.where(ContentVariant.kind == kind)
    res = await session.execute(q)
    return [ContentVariantOut.model_validate(v) for v in res.scalars().all()]


@router.get("/businesses/{business_id}/media", response_model=list[MediaAssetOut])
async def list_business_media(
    business_id: str, session: AsyncSession = Depends(get_session)
) -> list[MediaAssetOut]:
    res = await session.execute(
        select(MediaAsset)
        .where(MediaAsset.business_id == business_id)
        .order_by(MediaAsset.created_at.desc())
    )
    return [MediaAssetOut.model_validate(m) for m in res.scalars().all()]


# ---------------- background helpers ----------------


async def _background_research(business_id: str, tier) -> None:
    """Runs research right after a business is created so onboarding feels instant."""
    from app.db import session_factory

    async with session_factory()() as session:
        try:
            pipe = MarketingPipeline(tier=tier)
            await pipe.run_research(session, business_id)
        except Exception as e:
            from app.logging_config import get_logger
            get_logger(__name__).error("background_research_failed", error=str(e))
