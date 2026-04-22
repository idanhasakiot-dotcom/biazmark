"""End-to-end demo — drives the full pipeline via HTTP.

Prereqs: `docker compose up -d` (or backend running on :8000).

What it does:
    1. Creates a demo business
    2. Runs research → strategy → publish → optimize
    3. Prints each step so you can see the loop close

Usage:
    python scripts/seed_demo.py
    python scripts/seed_demo.py --base http://localhost:8000 --tier basic
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib import request as urlreq
from urllib.error import HTTPError


def req(method: str, url: str, body: dict[str, Any] | None = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    r = urlreq.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlreq.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode() or "null")
    except HTTPError as e:
        print(f"HTTP {e.code} on {method} {url}: {e.read().decode(errors='ignore')}")
        raise


def log(title: str, payload: Any = None) -> None:
    print(f"\n==== {title} ====")
    if payload is not None:
        s = json.dumps(payload, ensure_ascii=False, indent=2)
        if len(s) > 2000:
            s = s[:2000] + "\n... [truncated]"
        print(s)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--tier", default="basic", choices=["free", "basic", "pro", "enterprise"])
    parser.add_argument("--name", default="Acme Coffee Roasters")
    parser.add_argument("--website", default="")
    args = parser.parse_args()

    base = args.base.rstrip("/")

    log("Health check")
    print(req("GET", f"{base}/api/health"))

    log("Current tier")
    tier = req("GET", f"{base}/api/tier")
    print(tier)

    log("Available connectors")
    print(req("GET", f"{base}/api/connectors"))

    log("Creating demo business")
    biz = req(
        "POST",
        f"{base}/api/businesses",
        {
            "name": args.name,
            "description": (
                "Small-batch coffee roaster that ships fresh beans to home baristas. "
                "Direct trade relationships with 12 producers in Ethiopia + Colombia."
            ),
            "website": args.website,
            "industry": "specialty coffee, DTC food & beverage",
            "target_audience": (
                "Home espresso enthusiasts, 28-45, urban, disposable income, "
                "care about origin + freshness + sustainability."
            ),
            "goals": "drive first-time subscriptions, then retention",
            "tier": args.tier,
        },
    )
    biz_id = biz["id"]
    log("Business created", biz)

    # Background task kicked off research; give it a second to start.
    time.sleep(2)

    log("Running research (explicit)")
    research = req("POST", f"{base}/api/businesses/{biz_id}/research")
    log("Research summary", research.get("summary"))
    log("Competitors (first 3)", research.get("competitors", [])[:3])

    log("Generating strategy")
    strategy = req(
        "POST",
        f"{base}/api/businesses/{biz_id}/strategies",
        {"channels": ["meta", "linkedin", "preview"], "budget_hint": "$2k/mo, lean"},
    )
    log("Strategy", {k: strategy.get(k) for k in ["positioning", "value_prop", "channels"]})

    log("Publishing strategy (dry-run via preview connector)")
    campaigns = req(
        "POST",
        f"{base}/api/strategies/{strategy['id']}/publish",
        {"connector": "preview"},
    )
    log(f"Created {len(campaigns)} campaign(s)", [c["name"] for c in campaigns])

    if not campaigns:
        print("\nNo campaigns created — strategy had no channels?")
        return 1

    first = campaigns[0]
    log("First campaign variants")
    variants = req("GET", f"{base}/api/campaigns/{first['id']}/variants")
    for v in variants[:3]:
        print(f"  [{v['status']}] {v['headline']}")
        print(f"     {v['body'][:160]}...")

    log("Running optimize cycle on first campaign")
    event = req("POST", f"{base}/api/campaigns/{first['id']}/optimize")
    if event:
        log("Optimization event", {
            "headline": event["payload"].get("analysis", {}).get("headline"),
            "changes_applied": len(event["payload"].get("applied", [])),
        })

    log("Metrics snapshot")
    metrics = req("GET", f"{base}/api/campaigns/{first['id']}/metrics")
    print(f"  {len(metrics)} metric snapshots")

    print("\nDemo complete. Open the dashboard:")
    print(f"  http://localhost:3000/dashboard/{biz_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
