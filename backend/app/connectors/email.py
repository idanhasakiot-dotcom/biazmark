"""Email connector — Resend first, SendGrid fallback.

Credentials from ConnectorAccount or env:
    - api_key
    - from_email (domain must be verified with the provider)
    - to_list  (list of recipient emails or a placeholder for later merge)

This publishes a single broadcast per variant. For real list segments, extend to
accept a subscriber list from the DB or a mailing provider.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult
from app.logging_config import get_logger

log = get_logger(__name__)


class EmailConnector(BaseConnector):
    platform = "email"
    display_name = "Email (Resend/SendGrid)"

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        s = get_settings()
        self.resend_key = self.credentials.get("resend_api_key") or s.resend_api_key
        self.sendgrid_key = self.credentials.get("sendgrid_api_key") or s.sendgrid_api_key
        self.from_email = self.credentials.get("from_email") or s.email_from
        self.to_list: list[str] = self.credentials.get("to_list") or []

    async def connect(self) -> ConnectionStatus:
        if not (self.resend_key or self.sendgrid_key):
            return ConnectionStatus(connected=False, error="no email api key configured")
        if not self.from_email:
            return ConnectionStatus(connected=False, error="from_email not set")
        return ConnectionStatus(connected=True, account_name=self.from_email)

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        if not self.to_list:
            return PublishResult(external_id="", raw={"error": "no recipients — set to_list in connector credentials"})
        subject = variant.get("headline") or "(no subject)"
        html = variant.get("long_body") or f"<p>{variant.get('body', '')}</p>"
        text = variant.get("body") or ""
        if self.resend_key:
            return await self._send_resend(subject, html, text)
        return await self._send_sendgrid(subject, html, text)

    async def _send_resend(self, subject: str, html: str, text: str) -> PublishResult:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {self.resend_key}",
                             "Content-Type": "application/json"},
                    json={
                        "from": self.from_email,
                        "to": self.to_list,
                        "subject": subject,
                        "html": html,
                        "text": text,
                    },
                )
                r.raise_for_status()
                data = r.json()
            return PublishResult(external_id=data.get("id", ""), raw=data)
        except Exception as e:
            log.error("resend_send_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    async def _send_sendgrid(self, subject: str, html: str, text: str) -> PublishResult:
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {self.sendgrid_key}",
                             "Content-Type": "application/json"},
                    json={
                        "personalizations": [{"to": [{"email": e} for e in self.to_list]}],
                        "from": {"email": self.from_email},
                        "subject": subject,
                        "content": [
                            {"type": "text/plain", "value": text or " "},
                            {"type": "text/html", "value": html},
                        ],
                    },
                )
                r.raise_for_status()
                mid = r.headers.get("X-Message-Id", "")
            return PublishResult(external_id=mid, raw={"headers": dict(r.headers)})
        except Exception as e:
            log.error("sendgrid_send_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        # Email analytics (opens, clicks) require webhooks — stubbed for now.
        return [Metric(external_id=eid, raw={"note": "email analytics via webhooks"})
                for eid in external_ids]
