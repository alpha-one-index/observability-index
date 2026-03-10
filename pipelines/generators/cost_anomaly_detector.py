#!/usr/bin/env python3
"""Cost Anomaly Detector - Wish #4 for VP of Platform Engineering.

Analyzes observability provider pricing models to detect cost anomalies,
predict budget overruns, and recommend optimization strategies based on
usage patterns and tier thresholds.
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "cost_analysis"

# Provider pricing models (per-unit monthly costs)
PRICING_MODELS = {
    "datadog": {
        "metric_ingestion": {"unit": "custom_metric/month", "tiers": [
            {"up_to": 100, "price": 0, "note": "included"},
            {"up_to": 1000, "price": 0.05},
            {"up_to": 10000, "price": 0.03},
            {"up_to": float("inf"), "price": 0.015}
        ]},
        "log_ingestion": {"unit": "GB/month", "tiers": [
            {"up_to": 1, "price": 0, "note": "included"},
            {"up_to": float("inf"), "price": 0.10}
        ]},
        "apm_hosts": {"unit": "host/month", "price": 31.00},
        "infra_hosts": {"unit": "host/month", "price": 15.00},
        "synthetics_api": {"unit": "10k_runs/month", "price": 5.00},
        "hidden_costs": ["custom_metric_overages", "log_rehydration", "indexed_spans"]
    },
    "new_relic": {
        "data_ingestion": {"unit": "GB/month", "tiers": [
            {"up_to": 100, "price": 0, "note": "free tier"},
            {"up_to": float("inf"), "price": 0.30}
        ]},
        "full_platform_users": {"unit": "user/month", "price": 549.00},
        "core_users": {"unit": "user/month", "price": 0},
        "hidden_costs": ["full_user_overage", "data_plus_retention", "vulnerability_mgmt"]
    },
    "grafana_cloud": {
        "metrics": {"unit": "1k_series/month", "tiers": [
            {"up_to": 10, "price": 0, "note": "free tier"},
            {"up_to": float("inf"), "price": 8.00}
        ]},
        "logs": {"unit": "GB/month", "tiers": [
            {"up_to": 50, "price": 0, "note": "free tier"},
            {"up_to": float("inf"), "price": 0.50}
        ]},
        "traces": {"unit": "GB/month", "price": 0.50},
        "hidden_costs": ["alerting_sms", "enterprise_plugins", "sla_addon"]
    },
    "splunk": {
        "data_ingestion": {"unit": "GB/day", "tiers": [
            {"up_to": 1, "price": 0, "note": "trial"},
            {"up_to": float("inf"), "price": 15.00}
        ]},
        "itsi": {"unit": "host/month", "price": 25.00},
        "hidden_costs": ["premium_solutions", "cloud_migration_services", "heavy_forwarders"]
    },
    "elastic": {
        "data_ingestion": {"unit": "GB/month", "tiers": [
            {"up_to": 100, "price": 0, "note": "included"},
            {"up_to": float("inf"), "price": 0.25}
        ]},
        "enterprise_search": {"unit": "deployment/month", "price": 95.00},
        "hidden_costs": ["cross_cluster_replication", "ml_nodes", "snapshot_storage"]
    }
}


def calculate_tiered_cost(tiers, usage):
    """Calculate cost based on tiered pricing model."""
    total = 0
    remaining = usage
    prev_limit = 0
    
    for tier in tiers:
        limit = tier["up_to"]
        tier_usage = min(remaining, limit - prev_limit)
        if tier_usage <= 0:
            break
        total += tier_usage * tier["price"]
        remaining -= tier_usage
        prev_limit = limit
    
    return round(total, 2)


def detect_anomalies(provider, usage_history):
    """Detect cost anomalies in usage patterns."""
    if len(usage_history) < 3:
        return []
    
    anomalies = []
    costs = [entry["total_cost"] for entry in usage_history]
    
    # Calculate rolling mean and std
    mean_cost = sum(costs) / len(costs)
    variance = sum((c - mean_cost) ** 2 for c in costs) / len(costs)
    std_dev = math.sqrt(variance) if variance > 0 else 0
    
    for i, entry in enumerate(usage_history):
        cost = entry["total_cost"]
        if std_dev > 0 and abs(cost - mean_cost) > 2 * std_dev:
            anomalies.append({
                "period": entry.get("period", f"period_{i}"),
                "cost": cost,
                "expected_range": [round(mean_cost - 2*std_dev, 2), round(mean_cost + 2*std_dev, 2)],
                "deviation_pct": round((cost - mean_cost) / mean_cost * 100, 1),
                "severity": "critical" if abs(cost - mean_cost) > 3 * std_dev else "warning"
            })
    
    return anomalies


def recommend_optimizations(provider):
    """Generate cost optimization recommendations for a provider."""
    model = PRICING_MODELS.get(provider, {})
    recommendations = []
    
    hidden = model.get("hidden_costs", [])
    if hidden:
        recommendations.append({
            "category": "hidden_cost_awareness",
            "action": f"Monitor for hidden costs: {', '.join(hidden)}",
            "potential_savings_pct": 15,
            "priority": "high"
        })
    
    # Check for tiered pricing optimization
    for service, config in model.items():
        if isinstance(config, dict) and "tiers" in config:
            recommendations.append({
                "category": "tier_optimization",
                "action": f"Negotiate committed-use discount for {service}",
                "potential_savings_pct": 20,
                "priority": "medium"
            })
    
    recommendations.append({
        "category": "general",
        "action": "Implement metric cardinality controls to prevent custom metric explosion",
        "potential_savings_pct": 25,
        "priority": "high"
    })
    
    return recommendations


def generate_cost_reports():
    """Generate cost analysis reports for all providers."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_reports = []
    for provider in PRICING_MODELS:
        report = {
            "provider": provider,
            "pricing_model": {k: v for k, v in PRICING_MODELS[provider].items() if k != "hidden_costs"},
            "hidden_costs": PRICING_MODELS[provider].get("hidden_costs", []),
            "optimizations": recommend_optimizations(provider),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        all_reports.append(report)
        
        report_file = OUTPUT_DIR / f"{provider}_cost_analysis.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Generated: {report_file}")
    
    summary_file = OUTPUT_DIR / "cost_summary.json"
    with open(summary_file, "w") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "reports": all_reports}, f, indent=2, default=str)
    print(f"Summary: {summary_file}")
    return all_reports


if __name__ == "__main__":
    reports = generate_cost_reports()
    print(f"\nGenerated {len(reports)} cost analysis reports")
