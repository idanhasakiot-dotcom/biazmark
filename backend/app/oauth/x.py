"""X (Twitter) OAuth 2.0 with PKCE."""
from __future__ import annotations

import httpx

from app.oauth.base import AccountInfo, BaseOAuth, TokenSet


class XOAuth(BaseOAuth):
    platform = "x"
    auth_url = "https://twitter.com/i/oauth2/authorize"
    token_url = "https://api.twitter.com/2/oauth2/token"
    default_scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]
    use_pkce = True

    async def fetch_account(self, tokens: TokenSet) -> AccountInfo:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
                params={"user.fields": "id,name,username,verified"},
            )
            data = r.json().get("data", {}) if r.status_code == 200 else {}
        return AccountInfo(
            account_id=data.get("id", ""),
            display_name=data.get("name", "") or data.get("username", ""),
            meta={"username": data.get("username", "")},
        )
