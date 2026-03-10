#!/usr/bin/env python3
"""Cost Drift Detector - Proprietary scoring engine for ObservabilityIndex.

Detects and scores pricing drift across cloud/AI providers by tracking
historical cost signals, identifying anomalous price changes, and
quantifying cost volatility risk for each provider.

This is a proprietary algorithm unique to the ObservabilityIndex.
"""

import json
import statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path("data")
OUTPUT_DIR = Path("exports")
HISTORY_DIR = DATA_DIR / "cost_history"

# Drift detection thresholds
DRIFT_THRESHOLDS = {
    "minor": 0.05,      # 5% change
    "moderate": 0.15,   # 15% change
    "major": 0.30,      # 30% change
    "extreme": 0.50,    # 50% change
}

# Cost signal weights for composite drift score
COST_WEIGHTS = {
    "price_volatility": 0.25,
    "trend_direction": 0.20,
    "frequency_of_changes": 0.15,
    "magnitude_vs_peers": 0.15,
    "hidden_cost_signals": 0.10,
    "discount_stability": 0.10,
    "billing_transparency": 0.05,
}


def load_enriched_data() -> dict:
    enriched_path = DATA_DIR / "enriched" / "enriched_providers.json"
    if enriched_path.exists():
        with open(enriched_path) as f:
            return json.load(f)
    return {}


def load_cost_history(provider: str) -> list:
    hist_path = HISTORY_DIR / f"{provider.lower().replace(' ', '_')}.json"
    if hist_path.exists():
        with open(hist_path) as f:
            return json.load(f)
    return []


def calculate_price_volatility(history: list) -> float:
    if len(history) < 2:
        return 0.0
    prices = [h["normalized_cost"] for h in history if "normalized_cost" in h]
    if len(prices) < 2:
        return 0.0
    mean_price = statistics.mean(prices)
    if mean_price == 0:
        return 0.0
    std_dev = statistics.stdev(prices)
    cv = std_dev / mean_price
    volatility = min(cv * 100, 100)
    return round(volatility, 2)


def detect_trend_direction(history: list) -> dict:
    if len(history) < 3:
        return {"direction": "insufficient_data", "score": 50.0}
    prices = [h["normalized_cost"] for h in history if "normalized_cost" in h]
    if len(prices) < 3:
        return {"direction": "insufficient_data", "score": 50.0}
    recent = prices[-3:]
    older = prices[:-3] if len(prices) > 3 else prices[:1]
    recent_avg = statistics.mean(recent)
    older_avg = statistics.mean(older)
    if older_avg == 0:
        return {"direction": "stable", "score": 50.0}
    pct_change = (recent_avg - older_avg) / older_avg
    if pct_change > 0.10:
        direction = "increasing"
        score = max(0, 100 - (pct_change * 200))
    elif pct_change < -0.10:
        direction = "decreasing"
        score = min(100, 70 + abs(pct_change) * 100)
    else:
        direction = "stable"
        score = 65.0
    return {"direction": direction, "score": round(score, 2)}


def analyze_change_frequency(history: list) -> float:
    if len(history) < 2:
        return 50.0
    changes = 0
    for i in range(1, len(history)):
        prev = history[i - 1].get("normalized_cost", 0)
        curr = history[i].get("normalized_cost", 0)
        if prev > 0 and abs(curr - prev) / prev > 0.02:
            changes += 1
    change_rate = changes / (len(history) - 1)
    if change_rate > 0.7:
        return 20.0
    elif change_rate > 0.4:
        return 50.0
    elif change_rate > 0.1:
        return 75.0
    return 90.0


def compare_magnitude_vs_peers(provider_history: list, all_histories: dict) -> float:
    if not provider_history or not all_histories:
        return 50.0
    provider_prices = [h.get("normalized_cost", 0) for h in provider_history]
    if not provider_prices:
        return 50.0
    provider_latest = provider_prices[-1]
    peer_latest = []
    for name, hist in all_histories.items():
        prices = [h.get("normalized_cost", 0) for h in hist]
        if prices:
            peer_latest.append(prices[-1])
    if not peer_latest:
        return 50.0
    peer_avg = statistics.mean(peer_latest)
    if peer_avg == 0:
        return 50.0
    deviation = abs(provider_latest - peer_avg) / peer_avg
    if deviation > 0.5:
        return 20.0
    elif deviation > 0.25:
        return 45.0
    elif deviation > 0.1:
        return 65.0
    return 85.0


def detect_hidden_costs(provider_data: dict) -> float:
    hidden_signals = [
        "egress_fees", "api_surcharges", "support_tier_costs",
        "data_transfer_markup", "storage_tiering_penalties",
        "minimum_commit_required", "overage_multiplier",
    ]
    score = 100.0
    penalties_found = 0
    for signal in hidden_signals:
        if provider_data.get(signal):
            penalties_found += 1
    if penalties_found > 0:
        score -= penalties_found * 12
    return max(0.0, round(score, 2))


def assess_discount_stability(history: list) -> float:
    discounts = [h.get("discount_pct", 0) for h in history if "discount_pct" in h]
    if len(discounts) < 2:
        return 50.0
    mean_disc = statistics.mean(discounts)
    if mean_disc == 0:
        return 70.0
    std_disc = statistics.stdev(discounts) if len(discounts) > 1 else 0
    cv = std_disc / mean_disc if mean_disc > 0 else 0
    if cv > 0.5:
        return 25.0
    elif cv > 0.25:
        return 50.0
    elif cv > 0.1:
        return 70.0
    return 90.0


def evaluate_billing_transparency(provider_data: dict) -> float:
    transparency_indicators = [
        "public_pricing_page", "pricing_calculator",
        "cost_api_available", "billing_alerts",
        "usage_dashboard", "cost_export_api",
    ]
    found = sum(1 for ind in transparency_indicators if provider_data.get(ind))
    return round((found / len(transparency_indicators)) * 100, 2)


def classify_drift(drift_score: float) -> dict:
    if drift_score >= 85:
        return {"level": "minimal", "emoji": "green", "action": "monitor"}
    elif drift_score >= 70:
        return {"level": "low", "emoji": "yellow", "action": "watch"}
    elif drift_score >= 50:
        return {"level": "moderate", "emoji": "orange", "action": "review"}
    elif drift_score >= 30:
        return {"level": "high", "emoji": "red", "action": "alert"}
    return {"level": "critical", "emoji": "critical", "action": "immediate_review"}


def compute_drift_score(provider: str, provider_data: dict, all_histories: dict) -> dict:
    history = load_cost_history(provider)
    all_histories[provider] = history
    volatility = calculate_price_volatility(history)
    trend = detect_trend_direction(history)
    freq_score = analyze_change_frequency(history)
    peer_score = compare_magnitude_vs_peers(history, all_histories)
    hidden_score = detect_hidden_costs(provider_data)
    discount_score = assess_discount_stability(history)
    transparency_score = evaluate_billing_transparency(provider_data)
    sub_scores = {
        "price_volatility": round(100 - volatility, 2),
        "trend_direction": trend["score"],
        "frequency_of_changes": freq_score,
        "magnitude_vs_peers": peer_score,
        "hidden_cost_signals": hidden_score,
        "discount_stability": discount_score,
        "billing_transparency": transparency_score,
    }
    composite = sum(sub_scores[k] * COST_WEIGHTS[k] for k in COST_WEIGHTS)
    composite = round(composite, 1)
    drift_class = classify_drift(composite)
    return {
        "provider": provider,
        "drift_score": composite,
        "drift_classification": drift_class,
        "trend": trend["direction"],
        "sub_scores": sub_scores,
        "data_points": len(history),
        "cost_stable": composite >= 70,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def run_cost_drift_detection() -> dict:
    enriched = load_enriched_data()
    providers = enriched.get("providers", [])
    if isinstance(providers, dict):
        providers = list(providers.values())
    results = []
    all_histories = {}
    for p in providers:
        name = p.get("name", p.get("provider", "unknown"))
        result = compute_drift_score(name, p, all_histories)
        results.append(result)
    results.sort(key=lambda x: x["drift_score"], reverse=True)
    drift_scores = [r["drift_score"] for r in results]
    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "algorithm": "Cost Drift Detector v1.0",
        "weights": COST_WEIGHTS,
        "thresholds": DRIFT_THRESHOLDS,
        "providers": results,
        "summary": {
            "total_providers": len(results),
            "cost_stable_count": sum(1 for r in results if r["cost_stable"]),
            "avg_drift_score": round(statistics.mean(drift_scores), 1) if drift_scores else 0,
            "most_stable": results[0]["provider"] if results else None,
            "most_volatile": results[-1]["provider"] if results else None,
            "critical_alerts": sum(1 for r in results if r["drift_classification"]["level"] == "critical"),
        },
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "cost_drift_report.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Cost drift analyzed for {len(results)} providers")
    print(f"  Written to {out_path}")
    return output


if __name__ == "__main__":
    run_cost_drift_detection()
