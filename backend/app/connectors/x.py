"""X (Twitter) connector — posts tweets via v2 API.

Threads: if `long_body` is set and longer than 280 chars, we split on sentences and
post as a reply chain.
"""
from __future__ import annotations

import re
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult
from app.logging_config import get_logger

log = get_logger(__name__)
API = "https://api.twitter.com/2"


class XConnector(BaseConnector):
    platform = "x"
    display_name = "X (Twitter)"

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        self.token = self.credentials.get("access_token", "")

    async def connect(self) -> ConnectionStatus:
        if not self.token:
            return ConnectionStatus(connected=False, error="no access_token")
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(
                    f"{API}/users/me",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
                r.raise_for_status()
                data = r.json().get("data", {})
            return ConnectionStatus(
                connected=True,
                account_name=data.get("username", ""),
                raw=data,
            )
        except Exception as e:
            return ConnectionStatus(connected=False, error=str(e))

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        if not self.token:
            return PublishResult(external_id="", raw={"error": "no token"})
        chunks = _chunks_for(variant)
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                first_id: str | None = None
                reply_to: str | None = None
                for text in chunks:
                    payload: dict[str, Any] = {"text": text}
                    if reply_to:
                        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
                    r = await c.post(
                        f"{API}/tweets",
                        headers={"Authorization": f"Bearer {self.token}",
                                 "Content-Type": "application/json"},
                        json=payload,
                    )
                    r.raise_for_status()
                    tid = r.json()["data"]["id"]
                    first_id = first_id or tid
                    reply_to = tid
            return PublishResult(
                external_id=first_id or "",
                url=f"https://x.com/i/status/{first_id}" if first_id else "",
                raw={"tweet_count": len(chunks)},
            )
        except Exception as e:
            log.error("x_publish_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        if not self.token:
            return [Metric(external_id=eid) for eid in external_ids]
        out: list[Metric] = []
        async with httpx.AsyncClient(timeout=20) as c:
            for eid in external_ids:
                try:
                    r = await c.get(
                        f"{API}/tweets/{eid}",
                        headers={"Authorization": f"Bearer {self.token}"},
                        params={"tweet.fields": "public_metrics,non_public_metrics"},
                    )
                    data = r.json().get("data", {}) if r.status_code == 200 else {}
                    pm = data.get("public_metrics", {}) or {}
                    out.append(Metric(
                        external_id=eid,
                        impressions=int(pm.get("impression_count") or 0),
                        engagement=int(pm.get("like_count", 0)) + int(pm.get("retweet_count", 0))
                                   + int(pm.get("reply_count", 0)) + int(pm.get("quote_count", 0)),
                        clicks=0,
                        raw=pm,
                    ))
                except Exception as e:
                    out.append(Metric(external_id=eid, raw={"error": str(e)}))
        return out


def _chunks_for(variant: dict[str, Any]) -> list[str]:
    headline = variant.get("headline", "") or ""
    body = variant.get("body", "") or ""
    long_body = variant.get("long_body", "") or ""
    tags = variant.get("hashtags") or []
    tag_s = " ".join(f"#{t.lstrip('#')}" for t in tags)

    main = body or long_body
    full = f"{headline}\n\n{main}".strip()
    if tag_s:
        full += f"\n{tag_s}"
    if len(full) <= 280:
        return [full]

    # Split into sentences, repack into tweet-sized chunks.
    sentences = re.split(r"(?<=[\.\!\?])\s+", full)
    chunks: list[str] = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) + 1 <= 270:
            cur = (cur + " " + s).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = s
    if cur:
        chunks.append(cur)
    # Number them as a thread.
    total = len(chunks)
    return [f"{c} ({i + 1}/{total})" for i, c in enumerate(chunks)]
