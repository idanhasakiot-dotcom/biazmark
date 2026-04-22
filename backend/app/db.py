"""Database models + async session factory."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import Tier, get_settings


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSON, list[Any]: JSON}


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(String(500), default="")
    industry: Mapped[str] = mapped_column(String(200), default="")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[str] = mapped_column(Text, default="")
    tier: Mapped[Tier] = mapped_column(SAEnum(Tier), default=Tier.FREE)
    brief_raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    research: Mapped[list[Research]] = relationship(back_populates="business", cascade="all, delete-orphan")
    strategies: Mapped[list[Strategy]] = relationship(back_populates="business", cascade="all, delete-orphan")
    campaigns: Mapped[list[Campaign]] = relationship(back_populates="business", cascade="all, delete-orphan")


class Research(Base):
    __tablename__ = "research"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    summary: Mapped[str] = mapped_column(Text, default="")
    competitors: Mapped[list[Any]] = mapped_column(JSON, default=list)
    trends: Mapped[list[Any]] = mapped_column(JSON, default=list)
    audience_insights: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sources: Mapped[list[Any]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    business: Mapped[Business] = relationship(back_populates="research")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    version: Mapped[int] = mapped_column(default=1)
    positioning: Mapped[str] = mapped_column(Text, default="")
    value_prop: Mapped[str] = mapped_column(Text, default="")
    channels: Mapped[list[Any]] = mapped_column(JSON, default=list)
    messaging_pillars: Mapped[list[Any]] = mapped_column(JSON, default=list)
    kpis: Mapped[list[Any]] = mapped_column(JSON, default=list)
    budget_split: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    approved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    business: Mapped[Business] = relationship(back_populates="strategies")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"))
    name: Mapped[str] = mapped_column(String(300))
    channel: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft|live|paused|ended
    objective: Mapped[str] = mapped_column(String(100), default="awareness")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    business: Mapped[Business] = relationship(back_populates="campaigns")
    content_variants: Mapped[list[ContentVariant]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    metrics: Mapped[list[MetricSnapshot]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class ContentVariant(Base):
    __tablename__ = "content_variants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"))
    kind: Mapped[str] = mapped_column(String(50), default="post")  # post|ad|article|email|video|story|thread
    headline: Mapped[str] = mapped_column(String(500), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    long_body: Mapped[str] = mapped_column(Text, default="")  # article body, thread, etc.
    cta: Mapped[str] = mapped_column(String(200), default="")
    visual_prompt: Mapped[str] = mapped_column(Text, default="")
    media_url: Mapped[str] = mapped_column(String(1000), default="")  # image/video asset URL
    media_kind: Mapped[str] = mapped_column(String(50), default="")  # image|video|none
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(default=0.0)
    status: Mapped[str] = mapped_column(String(50), default="generated")  # generated|approved|rejected|live|killed
    external_id: Mapped[str] = mapped_column(String(300), default="")
    external_url: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    campaign: Mapped[Campaign] = relationship(back_populates="content_variants")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"))
    variant_id: Mapped[str] = mapped_column(ForeignKey("content_variants.id"), default="")
    impressions: Mapped[int] = mapped_column(default=0)
    clicks: Mapped[int] = mapped_column(default=0)
    conversions: Mapped[int] = mapped_column(default=0)
    spend: Mapped[float] = mapped_column(default=0.0)
    revenue: Mapped[float] = mapped_column(default=0.0)
    engagement: Mapped[int] = mapped_column(default=0)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    campaign: Mapped[Campaign] = relationship(back_populates="metrics")


class OptimizationEvent(Base):
    __tablename__ = "optimization_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), default="")
    kind: Mapped[str] = mapped_column(String(100))  # e.g. kill_variant, scale_variant, reframe, pivot
    reason: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ConnectorAccount(Base):
    __tablename__ = "connector_accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    platform: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(300), default="")
    # Encrypted blob — never read directly, always through app.vault.decrypt
    credentials_enc: Mapped[str] = mapped_column(Text, default="")
    # Non-sensitive public metadata (account id, page id, ad account id, scopes)
    account_meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="connected")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String, primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    platform: Mapped[str] = mapped_column(String(100))
    redirect_after: Mapped[str] = mapped_column(String(500), default="")
    code_verifier: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))
    variant_id: Mapped[str] = mapped_column(ForeignKey("content_variants.id"), default="")
    kind: Mapped[str] = mapped_column(String(50), default="image")  # image|video
    prompt: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(100), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    local_path: Mapped[str] = mapped_column(String(500), default="")
    width: Mapped[int] = mapped_column(default=0)
    height: Mapped[int] = mapped_column(default=0)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


# ---------- Session ----------

_engine = None
_SessionMaker: async_sessionmaker[AsyncSession] | None = None


def _normalize_db_url(url: str) -> str:
    """Railway / Heroku hand out `postgres://…` — SQLAlchemy + asyncpg need
    `postgresql+asyncpg://…`. Normalize so deploys don't choke on DATABASE_URL."""
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


def get_engine():
    global _engine, _SessionMaker
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            _normalize_db_url(settings.database_url), future=True, pool_pre_ping=True
        )
        _SessionMaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _SessionMaker is not None
    return _SessionMaker


async def get_session() -> AsyncSession:
    async with session_factory()() as s:
        yield s


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
