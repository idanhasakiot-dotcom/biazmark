"""OAuth flow orchestrator.

`start(business_id, platform)` →
    - creates random state + (optional) PKCE verifier
    - persists `OAuthState` row
    - returns the authorise URL to redirect the user to

`finish(state, code)` →
    - looks up the stored state
    - exchanges code → tokens
    - fetches account metadata
    - upserts an encrypted ConnectorAccount for (business, platform)

The API layer exposes two endpoints that call into this.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import ConnectorAccount, OAuthState
from app.logging_config import get_logger
from app.oauth.base import BaseOAuth, oauth_registry
from app.vault import encrypt

log = get_logger(__name__)


@dataclass
class StartResult:
    authorise_url: str
    state: str


class OAuthManager:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def _provider(self, platform: str) -> BaseOAuth:
        cls = oauth_registry.get(platform)
        if cls is None:
            raise LookupError(f"no oauth provider for {platform}")
        cid, csec = self._creds_for(platform)
        if not cid or not csec:
            raise LookupError(f"oauth client not configured for {platform} — set env vars")
        redirect_uri = f"{self.settings.oauth_redirect_base.rstrip('/')}/api/oauth/callback/{platform}"
        return cls(client_id=cid, client_secret=csec, redirect_uri=redirect_uri)

    def _creds_for(self, platform: str) -> tuple[str, str]:
        s = self.settings
        table = {
            "meta": (s.meta_app_id, s.meta_app_secret),
            "google": (s.google_client_id, s.google_client_secret),
            "linkedin": (s.linkedin_client_id, s.linkedin_client_secret),
            "tiktok": (s.tiktok_app_id, s.tiktok_app_secret),
            "x": (s.x_client_id, s.x_client_secret),
        }
        return table.get(platform, ("", ""))

    def platforms_configured(self) -> list[dict]:
        """Used by the UI — show which OAuth flows will work."""
        out = []
        for p in oauth_registry.platforms():
            cid, csec = self._creds_for(p)
            out.append({"platform": p, "configured": bool(cid and csec)})
        return out

    async def start(
        self, session: AsyncSession, business_id: str, platform: str, redirect_after: str = ""
    ) -> StartResult:
        provider = self._provider(platform)
        state = BaseOAuth.new_state()
        verifier = ""
        challenge: str | None = None
        if provider.use_pkce:
            verifier, challenge = BaseOAuth.new_pkce()
        url = provider.authorise_url(state=state, pkce_challenge=challenge)
        session.add(
            OAuthState(
                state=state,
                business_id=business_id,
                platform=platform,
                redirect_after=redirect_after,
                code_verifier=verifier,
            )
        )
        await session.commit()
        return StartResult(authorise_url=url, state=state)

    async def finish(
        self, session: AsyncSession, state: str, code: str
    ) -> ConnectorAccount:
        row = await session.get(OAuthState, state)
        if row is None:
            raise LookupError("unknown or expired oauth state")
        provider = self._provider(row.platform)
        tokens = await provider.exchange_code(code, code_verifier=row.code_verifier)
        account = await provider.fetch_account(tokens)

        # Upsert ConnectorAccount.
        res = await session.execute(
            select(ConnectorAccount).where(
                ConnectorAccount.business_id == row.business_id,
                ConnectorAccount.platform == row.platform,
            )
        )
        existing = res.scalar_one_or_none()
        enc_blob = encrypt({
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "scope": tokens.scope,
            "raw": tokens.raw,
        })
        expires_at = None
        if tokens.expires_in:
            expires_at = datetime.now(UTC) + timedelta(seconds=tokens.expires_in)

        if existing is None:
            existing = ConnectorAccount(
                business_id=row.business_id,
                platform=row.platform,
                display_name=account.display_name,
                credentials_enc=enc_blob,
                account_meta={"account_id": account.account_id, **account.meta},
                status="connected",
                expires_at=expires_at,
            )
            session.add(existing)
        else:
            existing.display_name = account.display_name
            existing.credentials_enc = enc_blob
            existing.account_meta = {"account_id": account.account_id, **account.meta}
            existing.status = "connected"
            existing.expires_at = expires_at

        await session.delete(row)  # one-shot state
        await session.commit()
        await session.refresh(existing)
        log.info("oauth_connected", platform=row.platform, business_id=row.business_id)
        return existing
