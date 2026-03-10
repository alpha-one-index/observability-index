#!/usr/bin/env python3
"""
Alpha Value Score™ — Proprietary composite model ranking (0-100).

The single number that answers: "Which AI model gives me the best
value RIGHT NOW?" Blends 6 real-time signals into one score that
no other index provides.

Formula (weighted composite):
  AVS = (Cost_Score * 0.25) + (Latency_Score * 0.20) + (Reliability_Score * 0.20)
        + (Throughput_Score * 0.15) + (RateLimit_Score * 0.10) + (Freshness_Score * 0.10)

Each sub-score is normalized 0-100 using min-max across the provider cohort,
then weighted. Higher = better value.

This is a proprietary algorithm by Alpha One Index.
"""

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "exports"

# Scoring weights (must sum to 1.0)
WEIGHTS = {
    "cost": 0.25,
    "latency": 0.20,
    "reliability": 0.20,
    "throughput": 0.15,
    "rate_limit": 0.10,
    "freshness": 0.10,
}

# Tier classification thresholds
TIER_THRESHOLDS = {
    "alpha_elite": 85,    # Top-tier: best-in-class value
    "alpha_strong": 70,   # Strong: reliable choice
    "alpha_moderate": 50, # Moderate: acceptable for non-critical
    "alpha_caution": 30,  # Caution: significant trade-offs
    # Below 30 = "alpha_avoid"
}


def normalize_min_max(values: list, invert: bool = False) -> list:
    """Normalize values to 0-100 scale. Invert=True for lower-is-better metrics."""
    if not values or all(v is None for v in values):
        return [50.0] * len(values)
    clean = [v for v in values if v is not None]
    if not clean:
        return [50.0] * len(values)
    min_v, max_v = min(clean), max(clean)
    if max_v == min_v:
        return [50.0] * len(values)
    result = []
    for v in values:
        if v is None:
            result.append(50.0)  # Unknown = median
        else:
            normalized = ((v - min_v) / (max_v - min_v)) * 100
            result.append(100 - normalized if invert else normalized)
    return result


def compute_cost_score(records: list) -> list:
    """Score based on cost per million tokens (lower cost = higher score)."""
    costs = []
    for r in records:
        input_cost = r.get("input_price_per_1m") or r.get("price_per_1m_input")
        output_cost = r.get("output_price_per_1m") or r.get("price_per_1m_output")
        if input_cost is not None and output_cost is not None:
            # Blended cost (assume 3:1 input:output ratio typical)
            costs.append(float(input_cost) * 0.75 + float(output_cost) * 0.25)
        elif input_cost is not None:
            costs.append(float(input_cost))
        else:
            costs.append(None)
    return normalize_min_max(costs, invert=True)


def compute_latency_score(records: list) -> list:
    """Score based on P95 latency (lower = higher score)."""
    latencies = []
    for r in records:
        p95 = r.get("latency_p95_ms") or r.get("latency_ms", {}).get("p95")
        if p95 is not None:
            latencies.append(float(p95))
        else:
            latencies.append(None)
    return normalize_min_max(latencies, invert=True)


def compute_reliability_score(records: list) -> list:
    """Score based on error rate and uptime (higher uptime = higher score)."""
    scores = []
    for r in records:
        error_rate = r.get("error_rate") or r.get("error_pct")
        uptime = r.get("uptime_pct")
        health = r.get("health")
        if uptime is not None:
            scores.append(float(uptime))
        elif error_rate is not None:
            scores.append(100 - float(error_rate))
        elif health == "healthy":
            scores.append(95.0)
        elif health == "degraded":
            scores.append(50.0)
        elif health == "down":
            scores.append(0.0)
        else:
            scores.append(None)
    return normalize_min_max(scores, invert=False)


def compute_throughput_score(records: list) -> list:
    """Score based on tokens/second throughput (higher = better)."""
    tps = []
    for r in records:
        throughput = r.get("throughput_tokens_per_sec") or r.get("tokens_per_second")
        if throughput is not None:
            tps.append(float(throughput))
        else:
            tps.append(None)
    return normalize_min_max(tps, invert=False)


def compute_rate_limit_score(records: list) -> list:
    """Score based on rate limit headroom (more remaining = better)."""
    headroom = []
    for r in records:
        remaining = r.get("rate_limit_remaining") or r.get("rate_limit_headers", {}).get(
            "x-ratelimit-remaining-requests"
        )
        if remaining is not None:
            headroom.append(float(remaining))
        else:
            headroom.append(None)
    return normalize_min_max(headroom, invert=False)


def compute_freshness_score(records: list) -> list:
    """Score based on how recently data was updated (newer = better)."""
    scores = []
    now = datetime.now(timezone.utc)
    for r in records:
        ts = r.get("last_updated") or r.get("timestamp")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                hours_old = (now - dt).total_seconds() / 3600
                # Decay: fresh (<1h) = 100, 24h = 50, 72h+ = 0
                scores.append(max(0, 100 - (hours_old * 100 / 72)))
            except (ValueError, TypeError):
                scores.append(None)
        else:
            scores.append(None)
    return normalize_min_max(scores, invert=False)


def classify_tier(score: float) -> str:
    """Classify a model into an Alpha tier."""
    if score >= TIER_THRESHOLDS["alpha_elite"]:
        return "alpha_elite"
    elif score >= TIER_THRESHOLDS["alpha_strong"]:
        return "alpha_strong"
    elif score >= TIER_THRESHOLDS["alpha_moderate"]:
        return "alpha_moderate"
    elif score >= TIER_THRESHOLDS["alpha_caution"]:
        return "alpha_caution"
    else:
        return "alpha_avoid"


def compute_alpha_scores(records: list) -> list:
    """Compute Alpha Value Score for each record in the dataset."""
    if not records:
        return []

    # Compute sub-scores across the full cohort
    cost_scores = compute_cost_score(records)
    latency_scores = compute_latency_score(records)
    reliability_scores = compute_reliability_score(records)
    throughput_scores = compute_throughput_score(records)
    rate_limit_scores = compute_rate_limit_score(records)
    freshness_scores = compute_freshness_score(records)

    scored_records = []
    for i, record in enumerate(records):
        sub_scores = {
            "cost": round(cost_scores[i], 1),
            "latency": round(latency_scores[i], 1),
            "reliability": round(reliability_scores[i], 1),
            "throughput": round(throughput_scores[i], 1),
            "rate_limit": round(rate_limit_scores[i], 1),
            "freshness": round(freshness_scores[i], 1),
        }

        # Weighted composite
        avs = sum(sub_scores[k] * WEIGHTS[k] for k in WEIGHTS)
        avs = round(avs, 1)

        tier = classify_tier(avs)

        scored_records.append({
            **record,
            "alpha_value_score": avs,
            "alpha_tier": tier,
            "alpha_sub_scores": sub_scores,
            "alpha_version": "1.0",
            "scored_at": datetime.now(timezone.utc).isoformat(),
        })

    return sorted(scored_records, key=lambda x: x["alpha_value_score"], reverse=True)


def run(records: Optional[list] = None) -> dict:
    """Score all records and export Alpha Value rankings."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Computing Alpha Value Scores...")

    if records is None:
        # Load from latest export
        latest = OUTPUT_DIR / "latest.json"
        if latest.exists():
            with open(latest) as f:
                data = json.load(f)
            records = data.get("records", [])
        else:
            records = []

    scored = compute_alpha_scores(records)

    # Tier distribution
    tier_dist = {}
    for r in scored:
        tier = r.get("alpha_tier", "unknown")
        tier_dist[tier] = tier_dist.get(tier, 0) + 1

    # Top performers
    top_5 = [{
        "provider": r.get("provider"),
        "model": r.get("model"),
        "alpha_value_score": r["alpha_value_score"],
        "alpha_tier": r["alpha_tier"],
    } for r in scored[:5]]

    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "algorithm": "Alpha Value Score v1.0",
        "methodology": {
            "weights": WEIGHTS,
            "tier_thresholds": TIER_THRESHOLDS,
            "normalization": "min-max across provider cohort",
        },
        "total_scored": len(scored),
        "tier_distribution": tier_dist,
        "top_performers": top_5,
        "rankings": scored,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "alpha_value_scores.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Scored {len(scored)} models")
    print(f"  Tier distribution: {tier_dist}")
    print(f"  Written to {out_path}")
    return output


if __name__ == "__main__":
    run()
