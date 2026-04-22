"""TikTok connector — uploads videos to the connected TikTok business account.

The TikTok Content Posting API is async: we POST a URL to the video, get a
`publish_id`, and the platform queues it for processing. Status polling can be
added later via the `/publish/status/fetch/` endpoint.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult
from app.logging_config import get_logger

log = get_logger(__name__)
API = "https://open.tiktokapis.com/v2"


class TikTokConnector(BaseConnector):
    platform = "tiktok"
    display_name = "TikTok"

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        self.token = self.credentials.get("access_token", "")

    async def connect(self) -> ConnectionStatus:
        if not self.token:
            return ConnectionStatus(connected=False, error="no access_token")
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    f"{API}/user/info/",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={"fields": "open_id,display_name,avatar_url"},
                )
                r.raise_for_status()
                data = r.json().get("data", {}).get("user", {})
            return ConnectionStatus(
                connected=True,
                account_name=data.get("display_name", ""),
                raw=data,
            )
        except Exception as e:
            return ConnectionStatus(connected=False, error=str(e))

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        if not self.token:
            return PublishResult(external_id="", raw={"error": "no token"})
        media_url = variant.get("media_url")
        if not media_url or variant.get("media_kind") != "video":
            return PublishResult(external_id="",
                                 raw={"error": "TikTok requires a video media_url"})
        caption = _format_caption(variant)
        try:
            async with httpx.AsyncClient(timeout=45) as c:
                r = await c.post(
                    f"{API}/post/publish/video/init/",
                    headers={"Authorization": f"Bearer {self.token}",
                             "Content-Type": "application/json; charset=UTF-8"},
                    json={
                        "post_info": {
                            "title": caption[:2200],
                            "privacy_level": "SELF_ONLY",  # safe default; operator can flip to PUBLIC
                            "disable_duet": False,
                            "disable_comment": False,
                            "disable_stitch": False,
                        },
                        "source_info": {
                            "source": "PULL_FROM_URL",
                            "video_url": media_url,
                        },
                    },
                )
                r.raise_for_status()
                pub_id = r.json().get("data", {}).get("publish_id", "")
            return PublishResult(external_id=pub_id, raw=r.json())
        except Exception as e:
            log.error("tiktok_publish_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        return [Metric(external_id=eid, raw={"note": "tiktok analytics API separate"})
                for eid in external_ids]


def _format_caption(variant: dict[str, Any]) -> str:
    parts = [variant.get("headline", ""), variant.get("body", "")]
    tags = variant.get("hashtags") or []
    if tags:
        parts.append(" ".join(f"#{t.lstrip('#')}" for t in tags))
    return "\n".join(p for p in parts if p).strip()
