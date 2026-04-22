"""Blog connector — publishes articles to WordPress via the REST API.

Credentials:
    - base_url: https://yourblog.com
    - username: WP user with publish permissions
    - app_password: WordPress Application Password (Settings → Users → Applications)

Publishes articles as `status=publish` by default (override with `status` in creds).
"""
from __future__ import annotations

import base64
from typing import Any

import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, ConnectionStatus, Metric, PublishResult
from app.logging_config import get_logger

log = get_logger(__name__)


class BlogConnector(BaseConnector):
    platform = "blog"
    display_name = "Blog (WordPress)"

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        s = get_settings()
        self.base = (self.credentials.get("base_url") or s.wordpress_base).rstrip("/")
        self.user = self.credentials.get("username") or s.wordpress_user
        self.pwd = self.credentials.get("app_password") or s.wordpress_app_password
        self.status = self.credentials.get("status", "publish")

    def _auth(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.user}:{self.pwd}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    async def connect(self) -> ConnectionStatus:
        if not (self.base and self.user and self.pwd):
            return ConnectionStatus(connected=False,
                                    error="set base_url, username, app_password for WordPress")
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(f"{self.base}/wp-json/wp/v2/users/me", headers=self._auth())
                r.raise_for_status()
                data = r.json()
            return ConnectionStatus(connected=True, account_name=data.get("name", self.user))
        except Exception as e:
            return ConnectionStatus(connected=False, error=str(e))

    async def publish(
        self, variant: dict[str, Any], campaign: dict[str, Any]
    ) -> PublishResult:
        if not (self.base and self.user and self.pwd):
            return PublishResult(external_id="", raw={"error": "not configured"})
        title = variant.get("headline") or "Untitled"
        body = variant.get("long_body") or variant.get("body") or ""
        excerpt = variant.get("body") or ""
        slug = (variant.get("meta") or {}).get("slug") or ""
        payload = {
            "title": title,
            "content": _md_to_html(body),
            "excerpt": excerpt[:500],
            "status": self.status,
        }
        if slug:
            payload["slug"] = slug
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post(
                    f"{self.base}/wp-json/wp/v2/posts",
                    headers={**self._auth(), "Content-Type": "application/json"},
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()
            return PublishResult(
                external_id=str(data.get("id", "")),
                url=data.get("link", ""),
                raw=data,
            )
        except Exception as e:
            log.error("blog_publish_failed", error=str(e))
            return PublishResult(external_id="", raw={"error": str(e)})

    async def fetch_metrics(self, external_ids: list[str]) -> list[Metric]:
        # WP core has no built-in page view stats — pair with Jetpack / GA4 later.
        return [Metric(external_id=eid, raw={"note": "pair with GA4 for analytics"})
                for eid in external_ids]


def _md_to_html(md: str) -> str:
    """Very small markdown-ish formatter. For real use, swap in `markdown` or `mistune`."""
    lines = md.splitlines()
    out: list[str] = []
    in_p = False
    for line in lines:
        if line.startswith("# "):
            if in_p:
                out.append("</p>")
                in_p = False
            out.append(f"<h1>{line[2:].strip()}</h1>")
        elif line.startswith("## "):
            if in_p:
                out.append("</p>")
                in_p = False
            out.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("### "):
            if in_p:
                out.append("</p>")
                in_p = False
            out.append(f"<h3>{line[4:].strip()}</h3>")
        elif not line.strip():
            if in_p:
                out.append("</p>")
                in_p = False
        else:
            if not in_p:
                out.append("<p>")
                in_p = True
            out.append(line)
    if in_p:
        out.append("</p>")
    return "\n".join(out)
