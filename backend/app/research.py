"""Research module — gathers raw signals to feed the Researcher agent.

Zero-cost path (Free tier): HTTP fetch + HTML parse of the business's own site,
plus Google Trends via `pytrends`. SerpAPI / SimilarWeb / competitor feeds kick in
for higher tiers if their keys are present.

Every gather_* returns structured, serialisable dicts — the agent decides what to
prioritise. This module never calls the LLM directly.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

import httpx
from selectolax.parser import HTMLParser

from app.config import Settings, get_settings
from app.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class Signals:
    own_site: dict[str, Any] = field(default_factory=dict)
    trends: list[dict[str, Any]] = field(default_factory=list)
    competitors: list[dict[str, Any]] = field(default_factory=list)
    search_results: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "own_site": self.own_site,
            "trends": self.trends,
            "competitors": self.competitors,
            "search_results": self.search_results,
            "_sources": self.sources,
        }


class ResearchGatherer:
    def __init__(self, settings: Settings | None = None, depth: str = "medium"):
        self.settings = settings or get_settings()
        self.depth = depth  # shallow|medium|deep|exhaustive

    async def gather(
        self,
        *,
        name: str,
        website: str,
        industry: str,
        keywords: list[str] | None = None,
    ) -> Signals:
        keywords = keywords or []
        if industry and industry not in keywords:
            keywords.append(industry)

        tasks: list[asyncio.Task] = []
        signals = Signals()

        if website:
            tasks.append(asyncio.create_task(self._fetch_site(website, signals)))
        if keywords and self.depth != "shallow":
            tasks.append(asyncio.create_task(self._fetch_trends(keywords, signals)))
        if keywords and self.settings.serpapi_key and self.depth in ("deep", "exhaustive"):
            tasks.append(asyncio.create_task(self._fetch_serp(keywords, signals)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return signals

    # ---------------- gatherers ----------------

    async def _fetch_site(self, url: str, signals: Signals) -> None:
        url = _normalise_url(url)
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "BiazmarkBot/0.1"})
                r.raise_for_status()
                html = r.text
            parsed = _parse_html(html)
            signals.own_site = {"url": url, **parsed}
            signals.sources.append({"kind": "own_site", "url": url})
        except Exception as e:
            log.warning("site_fetch_failed", url=url, error=str(e))
            signals.own_site = {"url": url, "error": str(e)}

    async def _fetch_trends(self, keywords: list[str], signals: Signals) -> None:
        """Google Trends via pytrends — runs in a thread because pytrends is sync."""
        try:
            loop = asyncio.get_running_loop()
            trends = await loop.run_in_executor(None, _pytrends_sync, keywords[:5])
            signals.trends = trends
            signals.sources.append({"kind": "google_trends", "keywords": keywords[:5]})
        except Exception as e:
            log.warning("trends_fetch_failed", error=str(e))

    async def _fetch_serp(self, keywords: list[str], signals: Signals) -> None:
        key = self.settings.serpapi_key
        if not key:
            return
        try:
            async with httpx.AsyncClient(timeout=20) as c:
                for q in keywords[:3]:
                    r = await c.get(
                        "https://serpapi.com/search.json",
                        params={"q": q, "api_key": key, "num": 10},
                    )
                    r.raise_for_status()
                    data = r.json()
                    organic = data.get("organic_results", []) or []
                    for item in organic[:10]:
                        signals.search_results.append(
                            {
                                "query": q,
                                "title": item.get("title"),
                                "link": item.get("link"),
                                "snippet": item.get("snippet"),
                            }
                        )
            signals.sources.append({"kind": "serpapi", "queries": keywords[:3]})
        except Exception as e:
            log.warning("serp_fetch_failed", error=str(e))


def _pytrends_sync(keywords: list[str]) -> list[dict[str, Any]]:
    """Synchronous pytrends call; returns simple list of rising-interest points."""
    try:
        from pytrends.request import TrendReq  # lazy import

        pt = TrendReq(hl="en-US", tz=0, timeout=(5, 15))
        pt.build_payload(kw_list=keywords, timeframe="today 3-m")
        df = pt.interest_over_time()
        if df is None or df.empty:
            return []
        out = []
        for kw in keywords:
            if kw in df.columns:
                series = df[kw].tolist()
                if series:
                    first, last = series[0], series[-1]
                    direction = (
                        "rising" if last > first * 1.1
                        else "declining" if last < first * 0.9
                        else "steady"
                    )
                    out.append(
                        {
                            "label": kw,
                            "direction": direction,
                            "first": first,
                            "last": last,
                            "max": max(series),
                        }
                    )
        return out
    except Exception as e:
        log.warning("pytrends_failed", error=str(e))
        return []


def _normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _parse_html(html: str) -> dict[str, Any]:
    tree = HTMLParser(html)
    title = (tree.css_first("title").text(strip=True) if tree.css_first("title") else "")
    desc_node = tree.css_first('meta[name="description"]')
    description = desc_node.attributes.get("content", "") if desc_node else ""
    h1s = [n.text(strip=True) for n in tree.css("h1")[:5]]
    h2s = [n.text(strip=True) for n in tree.css("h2")[:8]]
    text = " ".join(n.text(strip=True) for n in tree.css("p")[:30])
    text = re.sub(r"\s+", " ", text)[:4000]
    ogs: dict[str, str] = {}
    for n in tree.css('meta[property^="og:"]'):
        prop = n.attributes.get("property", "")
        ogs[prop] = n.attributes.get("content", "")
    return {
        "title": title,
        "description": description,
        "h1": h1s,
        "h2": h2s,
        "text_excerpt": text,
        "og": ogs,
    }
