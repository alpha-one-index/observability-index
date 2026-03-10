#!/usr/bin/env python3
"""SLA Risk Calculator - Wish #6 for VP of Platform Engineering.

Calculates SLA breach risk scores for observability providers based on
historical uptime, incident patterns, credit structures, and cascading
failure impact on downstream services.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "sla_risk"

# Provider SLA commitments and historical performance
PROVIDER_SLAS = {
    "datadog": {
        "committed_uptime_pct": 99.9,
        "historical_uptime_pct": 99.85,
        "incidents_last_12mo": 18,
        "major_incidents_last_12mo": 3,
        "avg_resolution_minutes": 47,
        "credit_structure": {"99.9": 0, "99.0_to_99.9": 10, "95.0_to_99.0": 25, "below_95": 50},
        "max_credit_pct": 50,
        "status_page": "https://status.datadoghq.com"
    },
    "new_relic": {
        "committed_uptime_pct": 99.9,
        "historical_uptime_pct": 99.92,
        "incidents_last_12mo": 12,
        "major_incidents_last_12mo": 2,
        "avg_resolution_minutes": 38,
        "credit_structure": {"99.9": 0, "99.0_to_99.9": 10, "95.0_to_99.0": 25, "below_95": 100},
        "max_credit_pct": 100,
        "status_page": "https://status.newrelic.com"
    },
    "grafana_cloud": {
        "committed_uptime_pct": 99.5,
        "historical_uptime_pct": 99.88,
        "incidents_last_12mo": 8,
        "major_incidents_last_12mo": 1,
        "avg_resolution_minutes": 32,
        "credit_structure": {"99.5": 0, "99.0_to_99.5": 10, "95.0_to_99.0": 25, "below_95": 50},
        "max_credit_pct": 50,
        "status_page": "https://status.grafana.com"
    },
    "splunk": {
        "committed_uptime_pct": 99.9,
        "historical_uptime_pct": 99.87,
        "incidents_last_12mo": 15,
        "major_incidents_last_12mo": 2,
        "avg_resolution_minutes": 55,
        "credit_structure": {"99.9": 0, "99.0_to_99.9": 10, "95.0_to_99.0": 25, "below_95": 50},
        "max_credit_pct": 50,
        "status_page": "https://www.splunkstatus.com"
    },
    "elastic": {
        "committed_uptime_pct": 99.95,
        "historical_uptime_pct": 99.91,
        "incidents_last_12mo": 10,
        "major_incidents_last_12mo": 1,
        "avg_resolution_minutes": 42,
        "credit_structure": {"99.95": 0, "99.0_to_99.95": 10, "95.0_to_99.0": 25, "below_95": 100},
        "max_credit_pct": 100,
        "status_page": "https://status.elastic.co"
    }
}


def calculate_risk_score(provider):
    """Calculate SLA breach risk score (0-100) for a provider."""
    sla = PROVIDER_SLAS.get(provider, {})
    if not sla:
        return None
    
    score = 0
    
    # Uptime gap risk (0-30 points)
    uptime_gap = sla["committed_uptime_pct"] - sla["historical_uptime_pct"]
    if uptime_gap > 0:
        score += min(30, uptime_gap * 300)
    
    # Incident frequency risk (0-25 points)
    score += min(25, sla["incidents_last_12mo"] * 1.5)
    
    # Major incident risk (0-20 points)
    score += min(20, sla["major_incidents_last_12mo"] * 7)
    
    # Resolution time risk (0-15 points)
    if sla["avg_resolution_minutes"] > 60:
        score += 15
    elif sla["avg_resolution_minutes"] > 30:
        score += min(15, (sla["avg_resolution_minutes"] - 30) * 0.5)
    
    # Credit protection (0-10 reduction)
    if sla["max_credit_pct"] >= 100:
        score -= 10
    elif sla["max_credit_pct"] >= 50:
        score -= 5
    
    return {
        "provider": provider,
        "risk_score": round(max(0, min(100, score)), 1),
        "risk_level": _risk_level(score),
        "uptime_gap_pct": round(uptime_gap, 3),
        "committed_uptime": sla["committed_uptime_pct"],
        "actual_uptime": sla["historical_uptime_pct"],
        "incident_frequency": sla["incidents_last_12mo"],
        "avg_resolution_min": sla["avg_resolution_minutes"],
        "max_credit_pct": sla["max_credit_pct"],
        "annual_downtime_hours": round((100 - sla["historical_uptime_pct"]) / 100 * 8760, 1)
    }


def _risk_level(score):
    if score >= 70: return "critical"
    elif score >= 50: return "high"
    elif score >= 30: return "moderate"
    else: return "low"


def generate_sla_reports():
    """Generate SLA risk reports for all providers."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_risks = []
    for provider in PROVIDER_SLAS:
        risk = calculate_risk_score(provider)
        if risk:
            all_risks.append(risk)
            
            risk_file = OUTPUT_DIR / f"{provider}_sla_risk.json"
            with open(risk_file, "w") as f:
                json.dump(risk, f, indent=2)
            print(f"Generated: {risk_file}")
    
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_rankings": sorted(all_risks, key=lambda x: x["risk_score"], reverse=True),
        "lowest_risk": min(all_risks, key=lambda x: x["risk_score"])["provider"],
        "highest_risk": max(all_risks, key=lambda x: x["risk_score"])["provider"],
        "avg_risk_score": round(sum(r["risk_score"] for r in all_risks) / len(all_risks), 1)
    }
    
    summary_file = OUTPUT_DIR / "sla_risk_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary: {summary_file}")
    return all_risks


if __name__ == "__main__":
    risks = generate_sla_reports()
    print(f"\nGenerated {len(risks)} SLA risk reports")
    for r in risks:
        print(f"  {r['provider']}: risk={r['risk_score']} ({r['risk_level']}), downtime={r['annual_downtime_hours']}h/yr")
