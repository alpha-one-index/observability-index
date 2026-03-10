"""ObservabilityIndex - Main Collection Pipeline

Aggregates data from all scrapers including live latency probes
and outage detection for unique real-time observability signals.
"""
import asyncio
import json
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from pipelines.scrapers.openai_models import fetch_openai
from pipelines.scrapers.anthropic_models import fetch_anthropic
from pipelines.scrapers.google_models import fetch_google
from pipelines.scrapers.live_latency_probe import run as run_latency_probe
from pipelines.scrapers.outage_detector import run as run_outage_detector
from pipelines.enrich import enrich_cost_efficiency


async def collect():
    all_records = []

    # --- Model catalog scrapers ---
    try:
        records = await fetch_openai()
        all_records.extend(records)
        print(f"[openai] {len(records)} records")
    except Exception as e:
        print(f"[openai] FAILED: {e}")

    try:
        records = await fetch_anthropic()
        all_records.extend(records)
        print(f"[anthropic] {len(records)} records")
    except Exception as e:
        print(f"[anthropic] FAILED: {e}")

    try:
        records = await fetch_google()
        all_records.extend(records)
        print(f"[google] {len(records)} records")
    except Exception as e:
        print(f"[google] FAILED: {e}")

    if not all_records:
        print("No data collected!")
        sys.exit(1)

    for record in all_records:
        enrich_cost_efficiency(record)

    os.makedirs("exports", exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    with open("exports/latest.json", "w") as f:
        json.dump({"generated": ts, "count": len(all_records), "records": all_records}, f, indent=2)

    if all_records:
        all_keys = []
        seen = set()
        for r in all_records:
            for k in r.keys():
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)
        with open("exports/latest.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore", restval="")
            writer.writeheader()
            writer.writerows(all_records)

    print(f"[export] {len(all_records)} records exported ({ts})")

    # --- Live observability probes (unique differentiators) ---
    print("\n--- Running live latency probes ---")
    try:
        probe_data = run_latency_probe()
        print(f"[latency_probe] {probe_data['summary']['healthy']}/{probe_data['summary']['total_providers']} providers healthy")
    except Exception as e:
        print(f"[latency_probe] FAILED: {e}")

    print("\n--- Running outage detector ---")
    try:
        outage_data = run_outage_detector()
        print(f"[outage_detector] Ecosystem: {outage_data['aggregate_health']['ecosystem_status']}")
    except Exception as e:
        print(f"[outage_detector] FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(collect())
