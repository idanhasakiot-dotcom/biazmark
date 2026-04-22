"""Meta connector — Facebook page posts + Instagram content + Ads Manager.

Credential resolution (from ConnectorAccount.credentials):
    - access_token (user token from OAuth, long-lived)
    - page_id — which FB page to post to  (from account_meta['pages'][i]['id'])
    - page_access_token — from account_meta['pages'][i]['access_token']
    - ig_business_id — account_meta['pages'][i]['instagram_business_account']['id']
    - ad_account_id  — account_meta['ad_accounts'][i]['id'] (format: act_XXXX)

Capabilities:
    - publish: creates an FB page post, optionally with attached image. For 'ad' kind,
      creates a Marketing API ad-creative + campaign + ad-set + ad.
    - fetch_metrics: uses Graph insights for posts, Marketing API insights for ads.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult
from app.logging_config import get_logger

log = get_logger(__name__)
GRAPH = "https://graph.facebook.com/v21.0"


class MetaConnector(BaseConnector):
    platform = "meta"
    display_name = "Meta (Facebook + Instagram)"

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        self.token = self.credentials.get("access_token") or get_settings().meta_access_token
        meta = self.credentials.get("_account_meta") or {}
        pages = meta.get("pages") or []
        primary_page = pages[0] if pages else {}
        self.page_id = self.credentials.get("page_id") or primary_page.get("id", "")
        self.page_token = (
            self.credentials.get("page_access_token") or primary_page.get("access_token", "") or self.token
        )
        self.ig_business_id = (
            self.credentials.get("ig_business_id")
            or (primary_page.get("instagram_business_account") or {}).get("id", "")
        )
        ad_accounts = meta.get("ad_accounts") or []
        self.ad_account_id = (
            self.credentials.get("ad_account_id")
            or (ad_accounts[0]["id"] if ad_accounts else "")
        )

    # ---- base interface ----

    async def connect(self) -> ConnectionStatus:
        if not self.token:
            return ConnectionStatus(connected=False, error="no access_token")
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(f"{GRAPH}/me", params={"access_token": self.token})
                r.raise_for_status()
                data = r.json()
            return ConnectionStatus(
                connected=True,
                account_name=data.get("name", ""),
                raw={
                    "page_id": self.page_id,
                    "ig_business_id": self.ig_business_id,
                    "ad_account_id": self.ad_account_id,
                },
            )
        except Exception as e:
            return ConnectionStatus(connected=False, error=str(e))

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        kind = (variant.get("kind") or "post").lower()
        if kind == "ad":
            return await self._publish_ad(variant, campaign)
        return await self._publish_post(variant, campaign)

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        if not self.token or not external_ids:
            return [Metric(external_id=eid) for eid in external_ids]
        out: list[Metric] = []
        async with httpx.AsyncClient(timeout=20) as c:
            for eid in external_ids:
                if eid.startswith("ad_"):
                    out.append(await self._fetch_ad_metrics(c, eid[3:]))
                else:
                    out.append(await self._fetch_post_metrics(c, eid))
        return out

    # ---- post publishing (organic) ----

    async def _publish_post(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        if not (self.page_id and self.page_token):
            log.warning("meta_missing_page_credentials")
            return PublishResult(external_id="", raw={"error": "page not configured"})
        message = _format_message(variant)
        media_url = variant.get("media_url")
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                if media_url and variant.get("media_kind") == "image":
                    r = await c.post(
                        f"{GRAPH}/{self.page_id}/photos",
                        data={"url": media_url, "caption": message, "access_token": self.page_token},
                    )
                else:
                    r = await c.post(
                        f"{GRAPH}/{self.page_id}/feed",
                        data={"message": message, "access_token": self.page_token},
                    )
                r.raise_for_status()
                data = r.json()
            pid = str(data.get("post_id") or data.get("id") or "")
            return PublishResult(
                external_id=pid,
                url=f"https://facebook.com/{pid}",
                raw=data,
            )
        except Exception as e:
            log.error("meta_post_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    # ---- ad publishing (paid) ----

    async def _publish_ad(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        if not (self.ad_account_id and self.page_id and self.token):
            return PublishResult(external_id="", raw={"error": "ad account not configured"})
        objective = {
            "awareness": "OUTCOME_AWARENESS",
            "consideration": "OUTCOME_TRAFFIC",
            "conversion": "OUTCOME_SALES",
            "retention": "OUTCOME_ENGAGEMENT",
        }.get(campaign.get("objective", "awareness"), "OUTCOME_AWARENESS")
        name = campaign.get("name") or "biazmark campaign"
        try:
            async with httpx.AsyncClient(timeout=45) as c:
                # 1. campaign
                cam = await c.post(
                    f"{GRAPH}/{self.ad_account_id}/campaigns",
                    data={
                        "name": name,
                        "objective": objective,
                        "status": "PAUSED",
                        "special_ad_categories": "[]",
                        "access_token": self.token,
                    },
                )
                cam.raise_for_status()
                campaign_id = cam.json()["id"]

                # 2. ad creative
                link_data = {
                    "message": variant.get("body") or "",
                    "link": "https://example.com",  # real brand url when available
                    "name": variant.get("headline") or "",
                    "description": variant.get("cta") or "",
                }
                if variant.get("media_url"):
                    link_data["picture"] = variant["media_url"]
                cr = await c.post(
                    f"{GRAPH}/{self.ad_account_id}/adcreatives",
                    data={
                        "name": f"creative:{variant.get('id', '')}",
                        "object_story_spec": str({"page_id": self.page_id, "link_data": link_data}).replace("'", '"'),
                        "access_token": self.token,
                    },
                )
                cr.raise_for_status()
                creative_id = cr.json()["id"]

                # 3. ad-set (minimal, 1-day $5 — paused so we don't spend by accident)
                ads = await c.post(
                    f"{GRAPH}/{self.ad_account_id}/adsets",
                    data={
                        "name": f"adset:{variant.get('id', '')}",
                        "campaign_id": campaign_id,
                        "daily_budget": "500",
                        "billing_event": "IMPRESSIONS",
                        "optimization_goal": "REACH",
                        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                        "status": "PAUSED",
                        "targeting": '{"geo_locations":{"countries":["US"]}}',
                        "access_token": self.token,
                    },
                )
                ads.raise_for_status()
                adset_id = ads.json()["id"]

                # 4. ad
                ad = await c.post(
                    f"{GRAPH}/{self.ad_account_id}/ads",
                    data={
                        "name": f"ad:{variant.get('id', '')}",
                        "adset_id": adset_id,
                        "creative": f'{{"creative_id": "{creative_id}"}}',
                        "status": "PAUSED",
                        "access_token": self.token,
                    },
                )
                ad.raise_for_status()
                ad_id = ad.json()["id"]

            return PublishResult(
                external_id=f"ad_{ad_id}",
                url=f"https://business.facebook.com/adsmanager/manage/ads?selected_ad_ids={ad_id}",
                raw={"campaign_id": campaign_id, "adset_id": adset_id, "ad_id": ad_id,
                     "creative_id": creative_id, "status": "paused"},
            )
        except Exception as e:
            log.error("meta_ad_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    # ---- metrics ----

    async def _fetch_post_metrics(self, c: httpx.AsyncClient, eid: str) -> Metric:
        try:
            r = await c.get(
                f"{GRAPH}/{eid}/insights",
                params={"metric": "post_impressions,post_clicks,post_engagements",
                        "access_token": self.page_token or self.token},
            )
            raw = r.json().get("data", []) if r.status_code == 200 else []
        except Exception as e:
            return Metric(external_id=eid, raw={"error": str(e)})
        def _v(name: str) -> int:
            for it in raw:
                if it.get("name") == name:
                    vs = it.get("values") or []
                    if vs:
                        return int(vs[0].get("value") or 0)
            return 0
        return Metric(
            external_id=eid,
            impressions=_v("post_impressions"),
            clicks=_v("post_clicks"),
            engagement=_v("post_engagements"),
        )

    async def _fetch_ad_metrics(self, c: httpx.AsyncClient, ad_id: str) -> Metric:
        try:
            r = await c.get(
                f"{GRAPH}/{ad_id}/insights",
                params={"fields": "impressions,clicks,spend,actions,action_values",
                        "access_token": self.token},
            )
            data = (r.json().get("data") or [{}])[0] if r.status_code == 200 else {}
        except Exception as e:
            return Metric(external_id=f"ad_{ad_id}", raw={"error": str(e)})
        conv = 0
        rev = 0.0
        for a in data.get("actions", []) or []:
            if a.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                conv += int(a.get("value") or 0)
        for a in data.get("action_values", []) or []:
            if a.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                rev += float(a.get("value") or 0)
        return Metric(
            external_id=f"ad_{ad_id}",
            impressions=int(data.get("impressions") or 0),
            clicks=int(data.get("clicks") or 0),
            spend=float(data.get("spend") or 0),
            conversions=conv,
            revenue=rev,
            raw=data,
        )


def _format_message(variant: dict[str, Any]) -> str:
    parts = [variant.get("headline", ""), variant.get("body", "")]
    cta = variant.get("cta")
    if cta:
        parts.append(f"\n{cta}")
    tags = variant.get("hashtags") or []
    if tags:
        parts.append("\n" + " ".join(f"#{t.lstrip('#')}" for t in tags))
    return "\n".join(p for p in parts if p).strip()
