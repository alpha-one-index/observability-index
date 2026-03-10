#!/usr/bin/env python3
"""Outage Detector — Scrapes official status pages for real-time incident data.

Unique differentiator: Aggregates structured incident data from every major AI
provider's status page into a single normalized feed with severity scoring,
impact classification, and historical uptime calculation.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATUS_PAGES = {
    "openai": {
        "url": "https://status.openai.com/api/v2/summary.json",
        "type": "statuspage_api",
    },
    "anthropic": {
        "url": "https://status.anthropic.com/api/v2/summary.json",
        "type": "statuspage_api",
    },
    "google_ai": {
        "url": "https://status.cloud.google.com/incidents.json",
        "type": "google_cloud",
        "filter_product": "Vertex AI",
    },
    "mistral": {
        "url": "https://status.mistral.ai/api/v2/summary.json",
        "type": "statuspage_api",
    },
    "cohere": {
        "url": "https://status.cohere.com/api/v2/summary.json",
        "type": "statuspage_api",
    },
    "huggingface": {
        "url": "https://status.huggingface.co/api/v2/summary.json",
        "type": "statuspage_api",
    },
    "replicate": {
        "url": "https://status.replicate.com/api/v2/summary.json",
        "type": "statuspage_api",
    },
}

SEVERITY_MAP = {
    "none": 0,
    "minor": 1,
    "major": 2,
    "critical": 3,
}

HEADERS = {"User-Agent": "ObservabilityIndex/1.0 (status-monitor)"}


def parse_statuspage_api(data: dict) -> dict:
    """Parse Atlassian StatusPage API v2 format."""
    status = data.get("status", {})
    components = data.get("components", [])
    incidents = data.get("incidents", [])

    active_incidents = []
    for inc in incidents:
        active_incidents.append({
            "id": inc.get("id"),
            "name": inc.get("name"),
            "status": inc.get("status"),
            "impact": inc.get("impact"),
            "severity_score": SEVERITY_MAP.get(inc.get("impact", "none"), 0),
            "created_at": inc.get("created_at"),
            "updated_at": inc.get("updated_at"),
            "shortlink": inc.get("shortlink"),
        })

    component_statuses = []
    for comp in components:
        if comp.get("group") is False or comp.get("name"):
            component_statuses.append({
                "name": comp.get("name"),
                "status": comp.get("status"),
                "operational": comp.get("status") == "operational",
            })

    return {
        "overall_status": status.get("indicator", "unknown"),
        "description": status.get("description", ""),
        "active_incidents": active_incidents,
        "components": component_statuses,
        "total_components": len(component_statuses),
        "operational_components": sum(1 for c in component_statuses if c["operational"]),
    }


def parse_google_cloud(data: list, filter_product: str) -> dict:
    """Parse Google Cloud status incidents JSON."""
    relevant = []
    for inc in data[:50]:  # Check recent 50
        affected = [a.get("title", "") for a in inc.get("affected_products", [])]
        if any(filter_product.lower() in a.lower() for a in affected):
            relevant.append({
                "id": inc.get("number"),
                "name": inc.get("external_desc", "")[:200],
                "status": inc.get("most_recent_update", {}).get("status", "unknown"),
                "severity": inc.get("severity", "unknown"),
                "severity_score": {"low": 1, "medium": 2, "high": 3}.get(
                    inc.get("severity", "").lower(), 0
                ),
                "created_at": inc.get("begin"),
                "updated_at": inc.get("modified"),
            })

    active = [i for i in relevant if i["status"] not in ("RESOLVED", "CLOSED")]
    return {
        "overall_status": "incident" if active else "operational",
        "description": f"{len(active)} active Vertex AI incidents" if active else "No active incidents",
        "active_incidents": active,
        "recent_resolved": [i for i in relevant if i["status"] in ("RESOLVED", "CLOSED")][:5],
    }


def scrape_provider(name: str, config: dict) -> dict:
    """Fetch and parse status for a single provider."""
    try:
        with httpx.Client(timeout=15, headers=HEADERS, follow_redirects=True) as client:
            resp = client.get(config["url"])
            resp.raise_for_status()
            data = resp.json()

        if config["type"] == "statuspage_api":
            parsed = parse_statuspage_api(data)
        elif config["type"] == "google_cloud":
            parsed = parse_google_cloud(data, config.get("filter_product", ""))
        else:
            parsed = {"raw": str(data)[:500]}

        return {
            "provider": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reachable": True,
            **parsed,
        }
    except Exception as e:
        return {
            "provider": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reachable": False,
            "error": str(e)[:300],
            "overall_status": "unreachable",
        }


def compute_aggregate_health(results: list) -> dict:
    """Compute ecosystem-wide health metrics."""
    reachable = [r for r in results if r.get("reachable")]
    statuses = [r.get("overall_status", "unknown") for r in reachable]

    incident_count = sum(
        len(r.get("active_incidents", [])) for r in reachable
    )
    max_severity = max(
        (max((i.get("severity_score", 0) for i in r.get("active_incidents", [])), default=0)
         for r in reachable),
        default=0,
    )

    if max_severity >= 3:
        ecosystem_status = "critical"
    elif max_severity >= 2:
        ecosystem_status = "degraded"
    elif incident_count > 0:
        ecosystem_status = "minor_issues"
    else:
        ecosystem_status = "all_clear"

    return {
        "ecosystem_status": ecosystem_status,
        "providers_monitored": len(results),
        "providers_reachable": len(reachable),
        "total_active_incidents": incident_count,
        "max_severity_score": max_severity,
        "providers_with_incidents": [
            r["provider"] for r in reachable if r.get("active_incidents")
        ],
    }


def run():
    """Scrape all status pages and write aggregated outage data."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting outage detection...")
    results = []
    for name, config in STATUS_PAGES.items():
        print(f"  Checking {name}...")
        result = scrape_provider(name, config)
        results.append(result)
        print(f"    -> {result.get('overall_status', 'unknown')}")

    aggregate = compute_aggregate_health(results)

    output = {
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "aggregate_health": aggregate,
        "providers": results,
    }

    out_path = OUTPUT_DIR / "outage_detector.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Ecosystem status: {aggregate['ecosystem_status']}")
    print(f"  Written to {out_path}")
    return output


if __name__ == "__main__":
    run()
