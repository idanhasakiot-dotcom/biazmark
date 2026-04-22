"""TikTok OAuth (Business)."""
from __future__ import annotations

import httpx

from app.oauth.base import AccountInfo, BaseOAuth, TokenSet


class TikTokOAuth(BaseOAuth):
    platform = "tiktok"
    auth_url = "https://business-api.tiktok.com/portal/auth"
    token_url = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
    default_scopes = ["user.info.basic", "video.list", "video.publish", "biz.creative.read"]

    async def fetch_account(self, tokens: TokenSet) -> AccountInfo:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://business-api.tiktok.com/open_api/v1.3/user/info/",
                headers={"Access-Token": tokens.access_token},
            )
            data = r.json() if r.status_code == 200 else {}
        info = (data.get("data") or {}).get("user") or {}
        return AccountInfo(
            account_id=info.get("open_id", ""),
            display_name=info.get("display_name", ""),
            meta=info,
        )
