"""Pydantic request/response schemas for the API layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.config import Tier


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    website: str = ""
    industry: str = ""
    target_audience: str = ""
    goals: str = ""
    tier: Tier = Tier.FREE
    brief_raw: dict[str, Any] = Field(default_factory=dict)


class BusinessOut(BaseModel):
    id: str
    name: str
    description: str
    website: str
    industry: str
    target_audience: str
    goals: str
    tier: Tier
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchOut(BaseModel):
    id: str
    business_id: str
    summary: str
    competitors: list[dict[str, Any]]
    trends: list[dict[str, Any]]
    audience_insights: dict[str, Any]
    sources: list[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyOut(BaseModel):
    id: str
    business_id: str
    version: int
    positioning: str
    value_prop: str
    channels: list[dict[str, Any]]
    messaging_pillars: list[dict[str, Any]]
    kpis: list[dict[str, Any]]
    budget_split: dict[str, Any]
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyRequest(BaseModel):
    channels: list[str] | None = None
    budget_hint: str = "lean"


class CampaignOut(BaseModel):
    id: str
    business_id: str
    strategy_id: str
    name: str
    channel: str
    objective: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ContentVariantOut(BaseModel):
    id: str
    campaign_id: str
    kind: str
    headline: str
    body: str
    long_body: str
    cta: str
    visual_prompt: str
    media_url: str
    media_kind: str
    meta: dict[str, Any]
    score: float
    status: str
    external_id: str
    external_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MediaAssetOut(BaseModel):
    id: str
    business_id: str
    variant_id: str
    kind: str
    prompt: str
    provider: str
    url: str
    width: int
    height: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectorAccountOut(BaseModel):
    id: str
    business_id: str
    platform: str
    display_name: str
    account_meta: dict[str, Any]
    status: str
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OAuthStartOut(BaseModel):
    authorise_url: str
    state: str


class ConnectorStatusOut(BaseModel):
    platform: str
    display_name: str
    oauth_supported: bool
    oauth_configured: bool
    connected: bool
    account_name: str = ""
    account_meta: dict[str, Any] = {}


class MetricOut(BaseModel):
    id: str
    campaign_id: str
    variant_id: str
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float
    engagement: int
    captured_at: datetime

    model_config = {"from_attributes": True}


class OptimizationEventOut(BaseModel):
    id: str
    business_id: str
    campaign_id: str
    kind: str
    reason: str
    payload: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class PublishRequest(BaseModel):
    connector: str = "preview"


class ConnectorOut(BaseModel):
    platform: str
    display_name: str
    supports_publish: bool
    supports_metrics: bool


class TierOut(BaseModel):
    tier: Tier
    llm_provider: str
    llm_model: str
    research_depth: str
    max_connectors: int
    loop_interval_seconds: int | None
    autonomous_agents: bool
    max_content_variants: int
