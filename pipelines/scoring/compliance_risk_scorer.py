#!/usr/bin/env python3
"""Compliance Risk Scorer - Proprietary scoring engine for ObservabilityIndex.

Scores each provider's compliance posture across regulatory frameworks
(SOC2, GDPR, HIPAA, ISO 27001, EU AI Act, etc.) and calculates a
composite compliance risk score with decay-based freshness weighting.

This is a proprietary algorithm unique to the ObservabilityIndex.
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path("data")
OUTPUT_DIR = Path("exports")

# Regulatory frameworks and their importance weights
FRAMEWORK_WEIGHTS = {
    "soc2_type2": 0.20,
    "gdpr": 0.18,
    "hipaa": 0.12,
    "iso_27001": 0.15,
    "eu_ai_act": 0.10,
    "ccpa": 0.08,
    "fedramp": 0.07,
    "pci_dss": 0.05,
    "nist_csf": 0.05,
}

# Certification freshness decay (months -> multiplier)
FRESHNESS_DECAY = {
    6: 1.0,
    12: 0.90,
    18: 0.75,
    24: 0.55,
    36: 0.30,
}

# Risk severity levels
RISK_LEVELS = {
    "low": {"min": 80, "color": "green"},
    "moderate": {"min": 60, "color": "yellow"},
    "elevated": {"min": 40, "color": "orange"},
    "high": {"min": 20, "color": "red"},
    "critical": {"min": 0, "color": "critical"},
}


def load_enriched_data() -> dict:
    path = DATA_DIR / "enriched" / "enriched_providers.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def calculate_freshness_multiplier(cert_date_str: Optional[str]) -> float:
    if not cert_date_str:
        return 0.3
    try:
        cert_date = datetime.fromisoformat(cert_date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return 0.3
    now = datetime.now(timezone.utc)
    months_old = (now - cert_date).days / 30.44
    for threshold, multiplier in sorted(FRESHNESS_DECAY.items()):
        if months_old <= threshold:
            return multiplier
    return 0.15


def score_framework(provider_data: dict, framework: str) -> dict:
    compliance = provider_data.get("compliance", {})
    framework_data = compliance.get(framework, {})
    if isinstance(framework_data, bool):
        base_score = 100.0 if framework_data else 0.0
        freshness = 0.7 if framework_data else 0.0
        return {
            "certified": framework_data,
            "base_score": base_score,
            "freshness_multiplier": freshness,
            "weighted_score": round(base_score * freshness, 2),
        }
    if isinstance(framework_data, dict):
        certified = framework_data.get("certified", False)
        cert_date = framework_data.get("certified_date") or framework_data.get("last_audit")
        base_score = 100.0 if certified else 0.0
        if not certified and framework_data.get("in_progress"):
            base_score = 40.0
        freshness = calculate_freshness_multiplier(cert_date) if certified else 0.0
        if not certified and framework_data.get("in_progress"):
            freshness = 0.5
        return {
            "certified": certified,
            "in_progress": framework_data.get("in_progress", False),
            "base_score": base_score,
            "freshness_multiplier": freshness,
            "weighted_score": round(base_score * freshness, 2),
        }
    return {
        "certified": False,
        "base_score": 0.0,
        "freshness_multiplier": 0.0,
        "weighted_score": 0.0,
    }


def detect_compliance_gaps(framework_scores: dict) -> list:
    gaps = []
    for fw, data in framework_scores.items():
        if not data.get("certified", False):
            severity = "critical" if FRAMEWORK_WEIGHTS.get(fw, 0) >= 0.15 else "moderate"
            gaps.append({
                "framework": fw,
                "severity": severity,
                "weight": FRAMEWORK_WEIGHTS.get(fw, 0),
                "in_progress": data.get("in_progress", False),
            })
    return sorted(gaps, key=lambda x: x["weight"], reverse=True)


def calculate_incident_penalty(provider_data: dict) -> float:
    incidents = provider_data.get("compliance_incidents", [])
    if not incidents:
        return 0.0
    penalty = 0.0
    now = datetime.now(timezone.utc)
    for inc in incidents:
        severity = inc.get("severity", "low")
        sev_penalty = {"critical": 15.0, "high": 10.0, "medium": 5.0, "low": 2.0}
        base = sev_penalty.get(severity, 2.0)
        inc_date_str = inc.get("date")
        if inc_date_str:
            try:
                inc_date = datetime.fromisoformat(inc_date_str.replace("Z", "+00:00"))
                months_ago = (now - inc_date).days / 30.44
                decay = max(0.1, 1.0 - (months_ago / 24))
                base *= decay
            except (ValueError, AttributeError):
                pass
        penalty += base
    return min(penalty, 40.0)


def classify_risk(score: float) -> dict:
    for level, config in RISK_LEVELS.items():
        if score >= config["min"]:
            return {"level": level, "color": config["color"]}
    return {"level": "critical", "color": "critical"}


def compute_compliance_score(provider: str, provider_data: dict) -> dict:
    framework_scores = {}
    for fw in FRAMEWORK_WEIGHTS:
        framework_scores[fw] = score_framework(provider_data, fw)
    composite = 0.0
    for fw, weight in FRAMEWORK_WEIGHTS.items():
        composite += framework_scores[fw]["weighted_score"] * weight
    composite = round(composite, 1)
    incident_penalty = calculate_incident_penalty(provider_data)
    final_score = max(0, round(composite - incident_penalty, 1))
    gaps = detect_compliance_gaps(framework_scores)
    risk = classify_risk(final_score)
    return {
        "provider": provider,
        "compliance_score": final_score,
        "raw_score": composite,
        "incident_penalty": round(incident_penalty, 2),
        "risk_classification": risk,
        "framework_scores": framework_scores,
        "compliance_gaps": gaps,
        "total_frameworks": len(FRAMEWORK_WEIGHTS),
        "certified_count": sum(1 for f in framework_scores.values() if f.get("certified")),
        "compliant": final_score >= 60,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def run_compliance_scoring() -> dict:
    enriched = load_enriched_data()
    providers = enriched.get("providers", [])
    if isinstance(providers, dict):
        providers = list(providers.values())
    results = []
    for p in providers:
        name = p.get("name", p.get("provider", "unknown"))
        result = compute_compliance_score(name, p)
        results.append(result)
    results.sort(key=lambda x: x["compliance_score"], reverse=True)
    scores = [r["compliance_score"] for r in results]
    import statistics
    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "algorithm": "Compliance Risk Scorer v1.0",
        "framework_weights": FRAMEWORK_WEIGHTS,
        "freshness_decay": FRESHNESS_DECAY,
        "providers": results,
        "summary": {
            "total_providers": len(results),
            "compliant_count": sum(1 for r in results if r["compliant"]),
            "avg_score": round(statistics.mean(scores), 1) if scores else 0,
            "most_compliant": results[0]["provider"] if results else None,
            "highest_risk": results[-1]["provider"] if results else None,
            "critical_gaps": sum(len(r["compliance_gaps"]) for r in results),
        },
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "compliance_risk_report.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Compliance scored for {len(results)} providers")
    print(f"  Written to {out_path}")
    return output


if __name__ == "__main__":
    run_compliance_scoring()
