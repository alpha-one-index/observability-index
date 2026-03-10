#!/usr/bin/env python3
"""Vendor Health Monitor - Wish #7 for VP of Platform Engineering.

Tracks observability vendor business health signals including funding,
acquisitions, employee growth, market position, and open-source commitment
to assess long-term viability and concentration risk.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "vendor_health"

# Vendor business health indicators
VENDOR_PROFILES = {
    "datadog": {
        "ticker": "DDOG",
        "public": True,
        "founded": 2010,
        "revenue_growth_yoy_pct": 26,
        "market_cap_b": 38.5,
        "employee_count": 5500,
        "employee_growth_pct": 12,
        "recent_acquisitions": ["Sqreen", "Ozcode", "CoScreen"],
        "oss_contributions": {"otel_contributor": True, "major_oss_projects": ["dd-agent", "dd-trace"]},
        "risk_signals": ["high_valuation_multiple", "competitive_pricing_pressure"]
    },
    "new_relic": {
        "ticker": "NEWR (acquired)",
        "public": False,
        "founded": 2008,
        "revenue_growth_yoy_pct": 8,
        "market_cap_b": 6.5,
        "employee_count": 2800,
        "employee_growth_pct": -5,
        "recent_acquisitions": ["Pixie Labs", "CodeStream"],
        "oss_contributions": {"otel_contributor": True, "major_oss_projects": ["newrelic-agent", "pixie"]},
        "risk_signals": ["private_equity_ownership", "workforce_reduction", "leadership_changes"]
    },
    "grafana_labs": {
        "ticker": "Private",
        "public": False,
        "founded": 2014,
        "revenue_growth_yoy_pct": 35,
        "market_cap_b": 6.0,
        "employee_count": 1200,
        "employee_growth_pct": 25,
        "recent_acquisitions": ["k6", "Asserts.ai"],
        "oss_contributions": {"otel_contributor": True, "major_oss_projects": ["grafana", "loki", "tempo", "mimir"]},
        "risk_signals": ["pre_ipo_uncertainty", "enterprise_monetization_challenge"]
    },
    "splunk": {
        "ticker": "SPLK (acquired by Cisco)",
        "public": False,
        "founded": 2003,
        "revenue_growth_yoy_pct": 11,
        "market_cap_b": 28.0,
        "employee_count": 8500,
        "employee_growth_pct": -8,
        "recent_acquisitions": ["SignalFx", "Plumbr", "Rigor"],
        "oss_contributions": {"otel_contributor": True, "major_oss_projects": ["opentelemetry-collector-contrib"]},
        "risk_signals": ["cisco_integration_uncertainty", "product_consolidation_risk", "workforce_reduction"]
    },
    "elastic": {
        "ticker": "ESTC",
        "public": True,
        "founded": 2012,
        "revenue_growth_yoy_pct": 18,
        "market_cap_b": 11.2,
        "employee_count": 3200,
        "employee_growth_pct": 5,
        "recent_acquisitions": ["Cmd", "build.security"],
        "oss_contributions": {"otel_contributor": True, "major_oss_projects": ["elasticsearch", "kibana", "beats"]},
        "risk_signals": ["license_model_controversy", "aws_competition"]
    }
}


def calculate_health_score(vendor):
    """Calculate vendor health score (0-100)."""
    profile = VENDOR_PROFILES.get(vendor, {})
    if not profile:
        return None
    
    score = 50  # baseline
    
    # Revenue growth (up to +20)
    growth = profile.get("revenue_growth_yoy_pct", 0)
    score += min(20, max(-20, growth - 10))
    
    # Employee growth (+/-10)
    emp_growth = profile.get("employee_growth_pct", 0)
    if emp_growth < 0:
        score -= min(10, abs(emp_growth))
    else:
        score += min(10, emp_growth / 3)
    
    # OSS commitment (+10)
    oss = profile.get("oss_contributions", {})
    if oss.get("otel_contributor"):
        score += 5
    score += min(5, len(oss.get("major_oss_projects", [])))
    
    # Risk signals (-5 each)
    score -= len(profile.get("risk_signals", [])) * 5
    
    # Public company transparency bonus
    if profile.get("public"):
        score += 5
    
    return {
        "vendor": vendor,
        "health_score": round(max(0, min(100, score)), 1),
        "health_rating": _health_rating(score),
        "revenue_growth": profile["revenue_growth_yoy_pct"],
        "employee_trend": "growing" if profile["employee_growth_pct"] > 0 else "shrinking",
        "risk_signal_count": len(profile.get("risk_signals", [])),
        "oss_commitment": "strong" if len(oss.get("major_oss_projects", [])) >= 3 else "moderate",
        "risk_signals": profile.get("risk_signals", [])
    }


def _health_rating(score):
    if score >= 75: return "excellent"
    elif score >= 60: return "good"
    elif score >= 40: return "fair"
    else: return "concerning"


def generate_health_reports():
    """Generate vendor health reports."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_health = []
    for vendor in VENDOR_PROFILES:
        health = calculate_health_score(vendor)
        if health:
            all_health.append(health)
            
            health_file = OUTPUT_DIR / f"{vendor}_health.json"
            with open(health_file, "w") as f:
                json.dump(health, f, indent=2)
            print(f"Generated: {health_file}")
    
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vendor_rankings": sorted(all_health, key=lambda x: x["health_score"], reverse=True),
        "healthiest": max(all_health, key=lambda x: x["health_score"])["vendor"],
        "most_concerning": min(all_health, key=lambda x: x["health_score"])["vendor"]
    }
    
    summary_file = OUTPUT_DIR / "vendor_health_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary: {summary_file}")
    return all_health


if __name__ == "__main__":
    reports = generate_health_reports()
    print(f"\nGenerated {len(reports)} vendor health reports")
    for r in reports:
        print(f"  {r['vendor']}: {r['health_score']} ({r['health_rating']})")
