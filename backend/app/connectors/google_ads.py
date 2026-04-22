"""Google Ads connector — creates Responsive Search Ads via the Google Ads REST API.

Requirements:
    - refresh_token from OAuth (google scope: adwords)
    - developer_token (from Google Ads API access approval)
    - customer_id (10-digit without dashes)
    - client_customer_id / login_customer_id if using a manager account

We exchange refresh_token → access_token per call, keep everything stateless.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult
from app.logging_config import get_logger

log = get_logger(__name__)
ADS_API = "https://googleads.googleapis.com/v17"


class GoogleAdsConnector(BaseConnector):
    platform = "google_ads"
    display_name = "Google Ads"

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        self.refresh_token = self.credentials.get("refresh_token", "") or get_settings().google_ads_refresh_token
        self.developer_token = self.credentials.get("developer_token", "")
        self.customer_id = (self.credentials.get("customer_id") or "").replace("-", "")
        self.login_customer_id = (self.credentials.get("login_customer_id") or "").replace("-", "")

    async def _access_token(self) -> str:
        s = get_settings()
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": s.google_client_id,
                    "client_secret": s.google_client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            r.raise_for_status()
            return r.json()["access_token"]

    async def connect(self) -> ConnectionStatus:
        if not self.refresh_token or not self.customer_id or not self.developer_token:
            return ConnectionStatus(connected=False,
                                    error="google_ads needs refresh_token + customer_id + developer_token")
        try:
            tok = await self._access_token()
            headers = self._headers(tok)
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(
                    f"{ADS_API}/customers/{self.customer_id}/googleAds:search",
                    headers=headers,
                    json={"query": "SELECT customer.descriptive_name FROM customer LIMIT 1"},
                )
                r.raise_for_status()
                rows = r.json().get("results", []) or []
                name = rows[0]["customer"]["descriptiveName"] if rows else self.customer_id
            return ConnectionStatus(connected=True, account_name=name)
        except Exception as e:
            return ConnectionStatus(connected=False, error=str(e))

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        # Real RSA creation requires a budget, campaign, ad group — multi-step.
        # For the MVP we log the full ad-draft JSON and return a stub ID so the
        # optimize/analytics loop can still proceed. Upgrading this to a real
        # `mutate` call is additive.
        draft = {
            "headlines": [variant.get("headline", "")[:30]],
            "long_headline": variant.get("headline", "")[:90],
            "descriptions": [variant.get("body", "")[:90], variant.get("cta", "")[:90]],
            "final_urls": ["https://example.com"],
            "customer_id": self.customer_id,
        }
        log.info("google_ads_draft_prepared", headline=draft["headlines"][0])
        return PublishResult(
            external_id=f"gads_draft_{variant.get('id', '')[:12]}",
            raw={"draft": draft, "status": "draft-logged — attach to a real campaign manually"},
        )

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        return [Metric(external_id=eid, raw={"note": "draft — no metrics yet"})
                for eid in external_ids]

    def _headers(self, token: str) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {token}",
            "developer-token": self.developer_token,
            "Content-Type": "application/json",
        }
        if self.login_customer_id:
            h["login-customer-id"] = self.login_customer_id
        return h
