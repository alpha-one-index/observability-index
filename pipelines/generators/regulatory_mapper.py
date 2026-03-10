#!/usr/bin/env python3
"""Regulatory Mapper - Wish #3 for VP of Platform Engineering.

Maps observability providers against regulatory frameworks (EU AI Act,
NIST CSF, SOC2, GDPR, HIPAA) to identify compliance gaps and generate
remediation roadmaps with priority scoring.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "regulatory"

# Regulatory framework requirements for observability platforms
REGULATORY_FRAMEWORKS = {
    "eu_ai_act": {
        "name": "EU AI Act",
        "effective_date": "2025-08-01",
        "requirements": {
            "logging_retention": {"min_days": 180, "description": "AI system logs must be retained for minimum 6 months"},
            "audit_trail": {"required": True, "description": "Complete audit trail for AI decision-making"},
            "data_sovereignty": {"eu_only": True, "description": "Data must reside within EU boundaries"},
            "explainability_metrics": {"required": True, "description": "Metrics tracking AI model explainability"},
            "human_oversight_logging": {"required": True, "description": "Log all human override actions"}
        },
        "penalty_max_pct": 6.0
    },
    "nist_csf": {
        "name": "NIST Cybersecurity Framework 2.0",
        "effective_date": "2024-02-26",
        "requirements": {
            "continuous_monitoring": {"required": True, "description": "Real-time security event monitoring"},
            "incident_detection": {"max_latency_sec": 300, "description": "Detect anomalies within 5 minutes"},
            "log_integrity": {"required": True, "description": "Tamper-evident logging with cryptographic verification"},
            "asset_inventory": {"required": True, "description": "Automated discovery and inventory of monitored assets"},
            "recovery_metrics": {"required": True, "description": "Track RTO/RPO metrics for all critical systems"}
        },
        "penalty_max_pct": 0
    },
    "soc2_type2": {
        "name": "SOC 2 Type II",
        "effective_date": "2024-01-01",
        "requirements": {
            "access_logging": {"required": True, "description": "Log all access to monitoring systems"},
            "change_management": {"required": True, "description": "Track all configuration changes with approval chain"},
            "availability_monitoring": {"uptime_pct": 99.9, "description": "Monitor and report platform availability"},
            "encryption_at_rest": {"required": True, "description": "All stored telemetry data must be encrypted"},
            "data_retention_policy": {"min_days": 365, "description": "Retain audit logs for minimum 1 year"}
        },
        "penalty_max_pct": 0
    },
    "gdpr": {
        "name": "GDPR",
        "effective_date": "2018-05-25",
        "requirements": {
            "data_minimization": {"required": True, "description": "Collect only necessary telemetry data"},
            "right_to_erasure": {"required": True, "description": "Support deletion of personal data from logs"},
            "data_processing_records": {"required": True, "description": "Maintain records of all data processing activities"},
            "breach_notification": {"max_hours": 72, "description": "Notify authorities within 72 hours of breach"},
            "dpia_support": {"required": True, "description": "Support Data Protection Impact Assessments"}
        },
        "penalty_max_pct": 4.0
    },
    "hipaa": {
        "name": "HIPAA",
        "effective_date": "1996-08-21",
        "requirements": {
            "phi_encryption": {"required": True, "description": "Encrypt all Protected Health Information in transit and at rest"},
            "access_controls": {"required": True, "description": "Role-based access with MFA for PHI data"},
            "audit_controls": {"required": True, "description": "Record and examine activity in systems containing PHI"},
            "automatic_logoff": {"required": True, "description": "Terminate sessions after inactivity period"},
            "baa_support": {"required": True, "description": "Business Associate Agreement available"}
        },
        "penalty_max_pct": 0
    }
}

# Provider compliance capabilities (what each provider supports)
PROVIDER_COMPLIANCE = {
    "datadog": {
        "eu_data_center": True,
        "log_retention_max_days": 450,
        "encryption_at_rest": True,
        "soc2_certified": True,
        "hipaa_baa": True,
        "audit_logging": True,
        "rbac": True,
        "data_deletion_api": False,
        "fedramp": True
    },
    "new_relic": {
        "eu_data_center": True,
        "log_retention_max_days": 395,
        "encryption_at_rest": True,
        "soc2_certified": True,
        "hipaa_baa": True,
        "audit_logging": True,
        "rbac": True,
        "data_deletion_api": True,
        "fedramp": False
    },
    "grafana_cloud": {
        "eu_data_center": True,
        "log_retention_max_days": 395,
        "encryption_at_rest": True,
        "soc2_certified": True,
        "hipaa_baa": False,
        "audit_logging": True,
        "rbac": True,
        "data_deletion_api": True,
        "fedramp": False
    },
    "splunk": {
        "eu_data_center": True,
        "log_retention_max_days": 730,
        "encryption_at_rest": True,
        "soc2_certified": True,
        "hipaa_baa": True,
        "audit_logging": True,
        "rbac": True,
        "data_deletion_api": False,
        "fedramp": True
    },
    "elastic": {
        "eu_data_center": True,
        "log_retention_max_days": 365,
        "encryption_at_rest": True,
        "soc2_certified": True,
        "hipaa_baa": True,
        "audit_logging": True,
        "rbac": True,
        "data_deletion_api": True,
        "fedramp": True
    }
}


def assess_compliance(provider, framework_id):
    """Assess a provider's compliance against a specific regulatory framework."""
    framework = REGULATORY_FRAMEWORKS.get(framework_id, {})
    capabilities = PROVIDER_COMPLIANCE.get(provider, {})
    
    if not framework or not capabilities:
        return None
    
    requirements = framework.get("requirements", {})
    gaps = []
    compliant = []
    
    for req_id, req_details in requirements.items():
        status = _check_requirement(req_id, req_details, capabilities)
        if status["met"]:
            compliant.append({"requirement": req_id, "details": req_details["description"]})
        else:
            gaps.append({
                "requirement": req_id,
                "details": req_details["description"],
                "remediation": status["remediation"],
                "priority": status["priority"]
            })
    
    total = len(requirements)
    score = (len(compliant) / total * 100) if total > 0 else 0
    
    return {
        "provider": provider,
        "framework": framework["name"],
        "framework_id": framework_id,
        "compliance_score": round(score, 1),
        "compliant_count": len(compliant),
        "gap_count": len(gaps),
        "total_requirements": total,
        "gaps": sorted(gaps, key=lambda x: x["priority"]),
        "compliant": compliant,
        "penalty_risk_pct": framework.get("penalty_max_pct", 0)
    }


def _check_requirement(req_id, req_details, capabilities):
    """Check if a provider capability meets a specific requirement."""
    checks = {
        "logging_retention": lambda: capabilities.get("log_retention_max_days", 0) >= req_details.get("min_days", 0),
        "data_sovereignty": lambda: capabilities.get("eu_data_center", False),
        "encryption_at_rest": lambda: capabilities.get("encryption_at_rest", False),
        "access_logging": lambda: capabilities.get("audit_logging", False),
        "access_controls": lambda: capabilities.get("rbac", False),
        "audit_controls": lambda: capabilities.get("audit_logging", False),
        "baa_support": lambda: capabilities.get("hipaa_baa", False),
        "phi_encryption": lambda: capabilities.get("encryption_at_rest", False),
        "right_to_erasure": lambda: capabilities.get("data_deletion_api", False),
        "data_retention_policy": lambda: capabilities.get("log_retention_max_days", 0) >= req_details.get("min_days", 0),
    }
    
    check_fn = checks.get(req_id)
    if check_fn and check_fn():
        return {"met": True, "remediation": None, "priority": 0}
    
    # Default: assume not met for unknown requirements
    priority = 1 if req_details.get("required", False) else 3
    remediation = f"Implement {req_id.replace('_', ' ')} capability"
    
    return {"met": check_fn() if check_fn else False, "remediation": remediation, "priority": priority}


def generate_regulatory_maps():
    """Generate compliance maps for all providers against all frameworks."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_assessments = []
    for provider in PROVIDER_COMPLIANCE:
        provider_results = []
        for framework_id in REGULATORY_FRAMEWORKS:
            assessment = assess_compliance(provider, framework_id)
            if assessment:
                provider_results.append(assessment)
                all_assessments.append(assessment)
        
        # Save per-provider report
        provider_file = OUTPUT_DIR / f"{provider}_regulatory_map.json"
        with open(provider_file, "w") as f:
            json.dump(provider_results, f, indent=2, default=str)
        print(f"Generated: {provider_file}")
    
    # Generate cross-provider summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frameworks_assessed": list(REGULATORY_FRAMEWORKS.keys()),
        "providers_assessed": list(PROVIDER_COMPLIANCE.keys()),
        "highest_risk_gaps": [
            a for a in all_assessments
            if a["gap_count"] > 0 and a["penalty_risk_pct"] > 0
        ],
        "provider_scores": {}
    }
    
    for provider in PROVIDER_COMPLIANCE:
        scores = [a["compliance_score"] for a in all_assessments if a["provider"] == provider]
        summary["provider_scores"][provider] = round(sum(scores) / len(scores), 1) if scores else 0
    
    summary_file = OUTPUT_DIR / "regulatory_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Summary: {summary_file}")
    
    return all_assessments


if __name__ == "__main__":
    assessments = generate_regulatory_maps()
    print(f"\nGenerated {len(assessments)} regulatory assessments")
    for a in assessments:
        print(f"  {a['provider']} vs {a['framework']}: {a['compliance_score']}% ({a['gap_count']} gaps)")
