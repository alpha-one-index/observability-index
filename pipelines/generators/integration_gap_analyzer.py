#!/usr/bin/env python3
"""Integration Gap Analyzer - Wish #5 for VP of Platform Engineering.

Maps integration ecosystems across observability providers to identify
coverage gaps, orphaned services, and recommends consolidation strategies
for multi-cloud and hybrid environments.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "integration_gaps"

# Integration categories and provider support
INTEGRATION_CATALOG = {
    "cloud_providers": {
        "aws": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "azure": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "gcp": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "oracle_cloud": {"datadog": False, "new_relic": True, "grafana_cloud": False, "splunk": True, "elastic": False},
        "ibm_cloud": {"datadog": False, "new_relic": False, "grafana_cloud": False, "splunk": True, "elastic": False}
    },
    "container_orchestration": {
        "kubernetes": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "openshift": {"datadog": True, "new_relic": True, "grafana_cloud": False, "splunk": True, "elastic": True},
        "ecs": {"datadog": True, "new_relic": True, "grafana_cloud": False, "splunk": True, "elastic": False},
        "nomad": {"datadog": True, "new_relic": False, "grafana_cloud": True, "splunk": False, "elastic": False}
    },
    "databases": {
        "postgresql": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "mongodb": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "redis": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "cassandra": {"datadog": True, "new_relic": True, "grafana_cloud": False, "splunk": True, "elastic": False},
        "cockroachdb": {"datadog": True, "new_relic": False, "grafana_cloud": True, "splunk": False, "elastic": False}
    },
    "ci_cd": {
        "github_actions": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "gitlab_ci": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "jenkins": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "argocd": {"datadog": True, "new_relic": False, "grafana_cloud": True, "splunk": False, "elastic": False},
        "tekton": {"datadog": False, "new_relic": False, "grafana_cloud": True, "splunk": False, "elastic": False}
    },
    "messaging": {
        "kafka": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "rabbitmq": {"datadog": True, "new_relic": True, "grafana_cloud": True, "splunk": True, "elastic": True},
        "pulsar": {"datadog": False, "new_relic": False, "grafana_cloud": True, "splunk": False, "elastic": False},
        "nats": {"datadog": False, "new_relic": False, "grafana_cloud": True, "splunk": False, "elastic": False}
    }
}

PROVIDERS = ["datadog", "new_relic", "grafana_cloud", "splunk", "elastic"]


def analyze_provider_gaps(provider):
    """Analyze integration gaps for a specific provider."""
    gaps = []
    supported = []
    total = 0
    
    for category, integrations in INTEGRATION_CATALOG.items():
        for integration, support in integrations.items():
            total += 1
            if support.get(provider, False):
                supported.append({"category": category, "integration": integration})
            else:
                # Find which providers do support it
                alternatives = [p for p in PROVIDERS if support.get(p, False) and p != provider]
                gaps.append({
                    "category": category,
                    "integration": integration,
                    "alternatives": alternatives,
                    "severity": "critical" if len(alternatives) >= 3 else "moderate"
                })
    
    coverage = (len(supported) / total * 100) if total > 0 else 0
    
    return {
        "provider": provider,
        "total_integrations": total,
        "supported_count": len(supported),
        "gap_count": len(gaps),
        "coverage_pct": round(coverage, 1),
        "gaps": gaps,
        "supported": supported
    }


def find_unique_integrations():
    """Find integrations uniquely supported by only one provider."""
    unique = {p: [] for p in PROVIDERS}
    
    for category, integrations in INTEGRATION_CATALOG.items():
        for integration, support in integrations.items():
            supporting = [p for p in PROVIDERS if support.get(p, False)]
            if len(supporting) == 1:
                unique[supporting[0]].append({"category": category, "integration": integration})
    
    return unique


def generate_gap_reports():
    """Generate integration gap reports for all providers."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_reports = []
    for provider in PROVIDERS:
        report = analyze_provider_gaps(provider)
        all_reports.append(report)
        
        report_file = OUTPUT_DIR / f"{provider}_integration_gaps.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Generated: {report_file}")
    
    unique = find_unique_integrations()
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_coverage": {r["provider"]: r["coverage_pct"] for r in all_reports},
        "unique_integrations": unique,
        "best_coverage": max(all_reports, key=lambda x: x["coverage_pct"])["provider"],
        "most_gaps": max(all_reports, key=lambda x: x["gap_count"])["provider"]
    }
    
    summary_file = OUTPUT_DIR / "integration_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary: {summary_file}")
    return all_reports


if __name__ == "__main__":
    reports = generate_gap_reports()
    print(f"\nGenerated {len(reports)} integration gap reports")
    for r in reports:
        print(f"  {r['provider']}: {r['coverage_pct']}% coverage ({r['gap_count']} gaps)")
