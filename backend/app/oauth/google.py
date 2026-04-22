"""Google OAuth — covers Google Ads + YouTube + GMB."""
from __future__ import annotations

import httpx

from app.oauth.base import AccountInfo, BaseOAuth, TokenSet


class GoogleOAuth(BaseOAuth):
    platform = "google"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    default_scopes = [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/adwords",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/business.manage",
    ]

    def authorise_url(self, state: str, scopes=None, pkce_challenge=None) -> str:
        # Google needs access_type=offline + prompt=consent to return a refresh_token.
        base = super().authorise_url(state, scopes, pkce_challenge)
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}access_type=offline&prompt=consent&include_granted_scopes=true"

    async def fetch_account(self, tokens: TokenSet) -> AccountInfo:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            r.raise_for_status()
            user = r.json()
        return AccountInfo(
            account_id=user.get("sub", ""),
            display_name=user.get("name", ""),
            meta={"email": user.get("email", "")},
        )
