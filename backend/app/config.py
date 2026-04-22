"""Runtime configuration — env-backed settings + tier definitions."""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Tier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TierSpec:
    """Describes what each tier is allowed to do and which model to use."""

    _SPECS: dict[Tier, dict] = {
        Tier.FREE: {
            "llm_provider": "ollama",
            "llm_model": "llama3.1:8b",
            "research_depth": "shallow",
            "max_connectors": 0,
            "loop_interval_seconds": None,  # manual
            "autonomous_agents": False,
            "max_content_variants": 2,
        },
        Tier.BASIC: {
            "llm_provider": "anthropic",
            "llm_model": "claude-haiku-4-5-20251001",
            "research_depth": "medium",
            "max_connectors": 1,
            "loop_interval_seconds": 86400,  # daily
            "autonomous_agents": False,
            "max_content_variants": 4,
        },
        Tier.PRO: {
            "llm_provider": "anthropic",
            "llm_model": "claude-sonnet-4-6",
            "research_depth": "deep",
            "max_connectors": 5,
            "loop_interval_seconds": 3600,  # hourly
            "autonomous_agents": False,
            "max_content_variants": 8,
        },
        Tier.ENTERPRISE: {
            "llm_provider": "anthropic",
            "llm_model": "claude-opus-4-7",
            "research_depth": "exhaustive",
            "max_connectors": 999,
            "loop_interval_seconds": 900,  # every 15 min
            "autonomous_agents": True,
            "max_content_variants": 16,
        },
    }

    @classmethod
    def for_tier(cls, tier: Tier) -> dict:
        return cls._SPECS[tier]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # Tier
    biazmark_tier: Tier = Tier.BASIC

    # LLM
    anthropic_api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # DB / Redis
    database_url: str = "postgresql+asyncpg://biazmark:biazmark@localhost:5432/biazmark"
    redis_url: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Auth
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 10080

    # Connectors — fallback env tokens (used if no per-business ConnectorAccount exists)
    meta_access_token: str = ""
    google_ads_refresh_token: str = ""
    linkedin_access_token: str = ""
    tiktok_access_token: str = ""
    x_bearer_token: str = ""

    # OAuth client apps (register apps with each platform, paste IDs/secrets here)
    oauth_redirect_base: str = "http://localhost:8000"
    meta_app_id: str = ""
    meta_app_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    tiktok_app_id: str = ""
    tiktok_app_secret: str = ""
    x_client_id: str = ""
    x_client_secret: str = ""

    # Media generation
    openai_api_key: str = ""
    replicate_api_token: str = ""
    stability_api_key: str = ""
    media_storage_dir: str = "./data/media"
    media_public_base: str = "http://localhost:8000/media"

    # Email + blog
    resend_api_key: str = ""
    sendgrid_api_key: str = ""
    email_from: str = ""
    wordpress_base: str = ""
    wordpress_user: str = ""
    wordpress_app_password: str = ""

    # Data sources
    serpapi_key: str = ""
    similarweb_api_key: str = ""

    log_level: str = "INFO"
    sentry_dsn: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def tier_spec(self) -> dict:
        return TierSpec.for_tier(self.biazmark_tier)


@lru_cache
def get_settings() -> Settings:
    return Settings()
