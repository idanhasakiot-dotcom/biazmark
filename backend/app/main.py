"""FastAPI application entry point."""
from __future__ import annotations

import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importing triggers registrations: connectors, oauth providers, media providers.
import app.connectors
import app.media
import app.oauth
from app import __version__
from app.api import router as api_router
from app.config import get_settings
from app.db import init_db
from app.logging_config import get_logger, setup_logging

setup_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("biazmark_starting", version=__version__, tier=settings.biazmark_tier.value)

    # Production safety checks — loud warnings, never crash.
    is_prod = settings.oauth_redirect_base.startswith("https://")
    if is_prod:
        if settings.secret_key in ("", "change-me", "change-me-in-production-please"):
            log.warning(
                "insecure_secret_key",
                message="SECRET_KEY is default in production — set a strong value "
                        "(e.g. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`).",
            )
        if not settings.anthropic_api_key and settings.biazmark_tier.value != "free":
            log.warning(
                "missing_anthropic_key",
                message="Tier is non-free but ANTHROPIC_API_KEY is empty — LLM calls will fail.",
            )

    await init_db()
    log.info("biazmark_ready")
    yield
    log.info("biazmark_shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Biazmark",
        version=__version__,
        description="Autonomous marketing system — brief in, campaigns out, self-improving.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    # Serve generated media assets.
    media_dir = pathlib.Path(settings.media_storage_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

    @app.get("/")
    async def root():
        return {"name": "biazmark", "version": __version__, "docs": "/docs"}

    # PaaS-standard health endpoints (Fly, Railway, Render, K8s all probe these).
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz():
        # Light DB round-trip to confirm the service can actually do work.
        from sqlalchemy import text

        from app.db import get_engine

        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            return {"status": "ok", "db": "ok"}
        except Exception as e:
            return {"status": "degraded", "db": str(e)}

    return app


app = create_app()
