"""Meta OAuth — Facebook + Instagram + Ads."""
from __future__ import annotations

import httpx

from app.oauth.base import AccountInfo, BaseOAuth, TokenSet


class MetaOAuth(BaseOAuth):
    platform = "meta"
    auth_url = "https://www.facebook.com/v21.0/dialog/oauth"
    token_url = "https://graph.facebook.com/v21.0/oauth/access_token"
    default_scopes = [
        "public_profile",
        "email",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_posts",
        "pages_manage_metadata",
        "instagram_basic",
        "instagram_content_publish",
        "ads_management",
        "ads_read",
        "business_management",
    ]

    async def fetch_account(self, tokens: TokenSet) -> AccountInfo:
        async with httpx.AsyncClient(timeout=15) as c:
            me = await c.get(
                "https://graph.facebook.com/v21.0/me",
                params={"access_token": tokens.access_token, "fields": "id,name,email"},
            )
            me.raise_for_status()
            user = me.json()
            pages = await c.get(
                "https://graph.facebook.com/v21.0/me/accounts",
                params={"access_token": tokens.access_token,
                        "fields": "id,name,access_token,instagram_business_account,category"},
            )
            pages.raise_for_status()
            pages_data = pages.json().get("data", [])
            ad_accounts = await c.get(
                "https://graph.facebook.com/v21.0/me/adaccounts",
                params={"access_token": tokens.access_token, "fields": "id,name,currency"},
            )
            ad_data = ad_accounts.json().get("data", []) if ad_accounts.status_code == 200 else []
        return AccountInfo(
            account_id=user.get("id", ""),
            display_name=user.get("name", ""),
            meta={
                "email": user.get("email", ""),
                "pages": pages_data,
                "ad_accounts": ad_data,
            },
        )
