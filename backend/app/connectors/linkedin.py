"""LinkedIn connector — posts to authenticated user's profile or organization.

Uses the LinkedIn UGC (User Generated Content) v2 API. To post to a company page,
pass `organization_urn` in credentials (format: 'urn:li:organization:XXXX').
"""
from __future__ import annotations

from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult
from app.logging_config import get_logger

log = get_logger(__name__)
API = "https://api.linkedin.com/v2"


class LinkedInConnector(BaseConnector):
    platform = "linkedin"
    display_name = "LinkedIn"

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        self.token = self.credentials.get("access_token", "")
        meta = self.credentials.get("_account_meta") or {}
        self.person_urn = self.credentials.get("person_urn") or (
            f"urn:li:person:{meta.get('account_id')}" if meta.get("account_id") else ""
        )
        self.organization_urn = self.credentials.get("organization_urn", "")

    async def connect(self) -> ConnectionStatus:
        if not self.token:
            return ConnectionStatus(connected=False, error="no access_token")
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(f"{API}/userinfo",
                                headers={"Authorization": f"Bearer {self.token}"})
                r.raise_for_status()
                data = r.json()
            return ConnectionStatus(connected=True, account_name=data.get("name", ""))
        except Exception as e:
            return ConnectionStatus(connected=False, error=str(e))

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        if not self.token:
            return PublishResult(external_id="", raw={"error": "no token"})
        author = self.organization_urn or self.person_urn
        if not author:
            return PublishResult(external_id="", raw={"error": "no author urn"})
        text = _format_text(variant)
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    f"{API}/ugcPosts",
                    headers={"Authorization": f"Bearer {self.token}",
                             "X-Restli-Protocol-Version": "2.0.0",
                             "Content-Type": "application/json"},
                    json=payload,
                )
                r.raise_for_status()
                urn = r.headers.get("x-restli-id") or r.json().get("id", "")
            post_id = urn.split(":")[-1] if urn else ""
            return PublishResult(
                external_id=urn,
                url=f"https://www.linkedin.com/feed/update/{urn}" if urn else "",
                raw={"post_id": post_id},
            )
        except Exception as e:
            log.error("linkedin_publish_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        # LinkedIn UGC metrics require the Marketing Developer Platform — stub for now.
        return [Metric(external_id=eid, raw={"note": "LinkedIn metrics require MDP access"})
                for eid in external_ids]


def _format_text(variant: dict[str, Any]) -> str:
    parts = [variant.get("headline", ""), variant.get("body", "")]
    cta = variant.get("cta")
    if cta:
        parts.append(f"\n→ {cta}")
    return "\n\n".join(p for p in parts if p).strip()
