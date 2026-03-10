#!/usr/bin/env python3
"""Executive Briefing Generator - Wish #8 for VP of Platform Engineering.

Aggregates all generator outputs into a single executive-ready briefing
document with key insights, risk summary, actionable recommendations,
and strategic outlook for observability platform decisions.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "executive_briefings"

# Import sibling generators
from pipelines.generators.unified_scorecard_generator import generate_scorecards
from pipelines.generators.migration_playbook_generator import generate_all_playbooks
from pipelines.generators.regulatory_mapper import generate_regulatory_maps
from pipelines.generators.cost_anomaly_detector import generate_cost_reports
from pipelines.generators.integration_gap_analyzer import generate_gap_reports
from pipelines.generators.sla_risk_calculator import generate_sla_reports
from pipelines.generators.vendor_health_monitor import generate_health_reports


def generate_executive_briefing():
    """Generate comprehensive executive briefing from all data sources."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Collecting data from all generators...")
    
    # Collect all data
    try:
        scorecards = generate_scorecards()
    except Exception:
        scorecards = []
    
    try:
        playbooks = generate_all_playbooks()
    except Exception:
        playbooks = []
    
    try:
        regulatory = generate_regulatory_maps()
    except Exception:
        regulatory = []
    
    try:
        cost_reports = generate_cost_reports()
    except Exception:
        cost_reports = []
    
    try:
        integration_gaps = generate_gap_reports()
    except Exception:
        integration_gaps = []
    
    try:
        sla_risks = generate_sla_reports()
    except Exception:
        sla_risks = []
    
    try:
        vendor_health = generate_health_reports()
    except Exception:
        vendor_health = []
    
    # Build executive briefing
    briefing = {
        "title": "Observability Platform Executive Briefing",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_sources": {
            "scorecards": len(scorecards),
            "migration_playbooks": len(playbooks),
            "regulatory_assessments": len(regulatory),
            "cost_analyses": len(cost_reports),
            "integration_reports": len(integration_gaps),
            "sla_risk_reports": len(sla_risks),
            "vendor_health_reports": len(vendor_health)
        },
        "key_findings": _extract_key_findings(
            scorecards, playbooks, regulatory,
            cost_reports, integration_gaps, sla_risks, vendor_health
        ),
        "risk_matrix": _build_risk_matrix(sla_risks, regulatory, vendor_health),
        "recommendations": _generate_recommendations(
            scorecards, sla_risks, integration_gaps, vendor_health
        )
    }
    
    briefing_file = OUTPUT_DIR / "executive_briefing.json"
    with open(briefing_file, "w") as f:
        json.dump(briefing, f, indent=2, default=str)
    print(f"\nExecutive briefing: {briefing_file}")
    
    return briefing


def _extract_key_findings(scorecards, playbooks, regulatory, costs, gaps, sla, health):
    """Extract top findings across all data sources."""
    findings = []
    
    if scorecards:
        top = max(scorecards, key=lambda x: x.get("overall_score", 0))
        findings.append({
            "category": "Overall Leader",
            "finding": f"{top.get('provider', 'Unknown')} leads with score {top.get('overall_score', 0)}",
            "impact": "high"
        })
    
    if sla:
        riskiest = max(sla, key=lambda x: x.get("risk_score", 0))
        findings.append({
            "category": "SLA Risk",
            "finding": f"{riskiest['provider']} has highest SLA breach risk at {riskiest['risk_score']}",
            "impact": "critical" if riskiest["risk_score"] > 50 else "moderate"
        })
    
    if gaps:
        worst_coverage = min(gaps, key=lambda x: x.get("coverage_pct", 100))
        findings.append({
            "category": "Integration Coverage",
            "finding": f"{worst_coverage['provider']} has lowest coverage at {worst_coverage['coverage_pct']}%",
            "impact": "moderate"
        })
    
    if health:
        concerning = min(health, key=lambda x: x.get("health_score", 100))
        findings.append({
            "category": "Vendor Health",
            "finding": f"{concerning['vendor']} shows concerning health score of {concerning['health_score']}",
            "impact": "high"
        })
    
    return findings


def _build_risk_matrix(sla_risks, regulatory, vendor_health):
    """Build consolidated risk matrix."""
    matrix = {}
    
    for risk in sla_risks:
        provider = risk.get("provider", "unknown")
        matrix.setdefault(provider, {})["sla_risk"] = risk.get("risk_score", 0)
    
    for assessment in regulatory:
        provider = assessment.get("provider", "unknown")
        matrix.setdefault(provider, {})["compliance_gaps"] = assessment.get("gap_count", 0)
    
    for health in vendor_health:
        vendor = health.get("vendor", "unknown")
        matrix.setdefault(vendor, {})["health_score"] = health.get("health_score", 0)
    
    return matrix


def _generate_recommendations(scorecards, sla, gaps, health):
    """Generate strategic recommendations."""
    recs = []
    
    recs.append({
        "priority": 1,
        "category": "Risk Mitigation",
        "action": "Implement multi-vendor observability strategy to reduce concentration risk",
        "timeline": "Q1-Q2"
    })
    
    recs.append({
        "priority": 2,
        "category": "Cost Optimization",
        "action": "Negotiate committed-use discounts with primary vendor based on usage analysis",
        "timeline": "Q1"
    })
    
    recs.append({
        "priority": 3,
        "category": "Compliance",
        "action": "Address EU AI Act gaps before August 2025 enforcement deadline",
        "timeline": "Q1-Q2"
    })
    
    recs.append({
        "priority": 4,
        "category": "Migration Readiness",
        "action": "Deploy OpenTelemetry Collector as abstraction layer for vendor portability",
        "timeline": "Q2-Q3"
    })
    
    return recs


if __name__ == "__main__":
    briefing = generate_executive_briefing()
    print(f"\nBriefing generated with {len(briefing['key_findings'])} key findings")
    print(f"Recommendations: {len(briefing['recommendations'])}")
