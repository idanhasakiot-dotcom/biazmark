"""LinkedIn OAuth."""
from __future__ import annotations

import httpx

from app.oauth.base import AccountInfo, BaseOAuth, TokenSet


class LinkedInOAuth(BaseOAuth):
    platform = "linkedin"
    auth_url = "https://www.linkedin.com/oauth/v2/authorization"
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    default_scopes = ["openid", "profile", "email", "w_member_social", "r_organization_admin", "w_organization_social"]

    async def fetch_account(self, tokens: TokenSet) -> AccountInfo:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            r.raise_for_status()
            data = r.json()
        return AccountInfo(
            account_id=data.get("sub", ""),
            display_name=data.get("name", ""),
            meta={"email": data.get("email", "")},
        )
