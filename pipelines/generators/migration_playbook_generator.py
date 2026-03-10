#!/usr/bin/env python3
"""Migration Playbook Generator - Wish #3 for VP of Platform Engineering.

Generates concrete migration playbooks per provider using lock-in scores,
open standards mapping, and competitor import capabilities to produce
actionable escape plans with estimated complexity and engineering hours.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "playbooks"

# Provider knowledge base - standards support and migration paths
PROVIDER_STANDARDS = {
    "datadog": {
        "supports": ["opentelemetry", "prometheus", "statsd", "fluentd"],
        "proprietary": ["datadog_agent", "dql", "notebooks", "synthetics"],
        "import_from": ["prometheus", "cloudwatch", "stackdriver"],
        "export_to": ["s3", "azure_blob", "gcs"],
        "migration_tools": False,
        "estimated_complexity": "high",
    },
    "new_relic": {
        "supports": ["opentelemetry", "prometheus", "grafana", "fluentd"],
        "proprietary": ["nrql", "nerdgraph", "nerdpacks"],
        "import_from": ["prometheus", "opentelemetry"],
        "export_to": ["s3", "nrdb_export"],
        "migration_tools": True,
        "estimated_complexity": "medium",
    },
    "grafana_cloud": {
        "supports": ["opentelemetry", "prometheus", "loki", "tempo", "mimir"],
        "proprietary": [],
        "import_from": ["prometheus", "elasticsearch", "cloudwatch"],
        "export_to": ["prometheus_remote_write", "s3"],
        "migration_tools": True,
        "estimated_complexity": "low",
    },
    "splunk": {
        "supports": ["opentelemetry", "fluentd", "syslog"],
        "proprietary": ["spl", "splunk_forwarder", "splunk_apps"],
        "import_from": ["syslog", "fluentd"],
        "export_to": ["s3", "hec"],
        "migration_tools": False,
        "estimated_complexity": "very_high",
    },
    "elastic": {
        "supports": ["opentelemetry", "prometheus", "fluentd", "beats"],
        "proprietary": ["eql", "kibana_dashboards", "elastic_agent"],
        "import_from": ["prometheus", "opentelemetry", "fluentd"],
        "export_to": ["s3", "elasticsearch_api"],
        "migration_tools": True,
        "estimated_complexity": "medium",
    },
}



def calculate_lock_in_score(provider):
    """Calculate vendor lock-in score (0-100) based on proprietary dependencies."""
    info = PROVIDER_STANDARDS.get(provider, {})
    if not info:
        return 100
    
    proprietary_count = len(info.get("proprietary", []))
    supports_otel = "opentelemetry" in info.get("supports", [])
    has_migration = info.get("migration_tools", False)
    import_options = len(info.get("import_from", []))
    export_options = len(info.get("export_to", []))
    
    score = min(100, proprietary_count * 15)
    if not supports_otel:
        score += 20
    if not has_migration:
        score += 15
    score -= min(20, (import_options + export_options) * 3)
    
    complexity_map = {"low": -10, "medium": 0, "high": 10, "very_high": 20}
    score += complexity_map.get(info.get("estimated_complexity", "medium"), 0)
    
    return max(0, min(100, score))


def generate_escape_plan(provider):
    """Generate step-by-step migration escape plan for a provider."""
    info = PROVIDER_STANDARDS.get(provider, {})
    lock_in = calculate_lock_in_score(provider)
    steps = []
    
    # Phase 1: Assessment
    steps.append({
        "phase": 1,
        "name": "Inventory & Assessment",
        "actions": [
            f"Catalog all {provider} dashboards, alerts, and integrations",
            "Map proprietary query languages to OpenTelemetry equivalents",
            "Identify data retention requirements and export windows",
            f"Estimate engineering effort: {_estimate_hours(lock_in)} hours"
        ],
        "estimated_days": 5
    })
    
    # Phase 2: Data Export
    export_targets = info.get("export_to", ["manual"])
    steps.append({
        "phase": 2,
        "name": "Data Export & Backup",
        "actions": [
            f"Export historical metrics via: {', '.join(export_targets)}",
            "Convert proprietary dashboards to Grafana JSON format",
            "Archive alert rules in OpenTelemetry-compatible format",
            "Validate data integrity with checksum verification"
        ],
        "estimated_days": 10 if lock_in > 50 else 5
    })
    
    # Phase 3: Migration Execution
    import_sources = info.get("import_from", [])
    steps.append({
        "phase": 3,
        "name": "Migration Execution",
        "actions": [
            "Deploy OpenTelemetry Collector as parallel ingestion layer",
            f"Configure import adapters: {', '.join(import_sources) if import_sources else 'manual migration required'}",
            "Run dual-write validation for 7-14 days",
            "Migrate alert rules and notification channels",
            "Perform load testing on new observability stack"
        ],
        "estimated_days": 15 if lock_in > 70 else 10
    })
    
    # Phase 4: Cutover
    steps.append({
        "phase": 4,
        "name": "Cutover & Decommission",
        "actions": [
            "Switch production traffic to new observability platform",
            f"Decommission {provider} agents and collectors",
            "Update runbooks and incident response procedures",
            "Conduct team training on new platform",
            "Monitor for 30 days before canceling old contracts"
        ],
        "estimated_days": 10
    })
    
    return {
        "provider": provider,
        "lock_in_score": lock_in,
        "total_estimated_days": sum(s["estimated_days"] for s in steps),
        "phases": steps
    }


def _estimate_hours(lock_in_score):
    """Convert lock-in score to estimated engineering hours."""
    if lock_in_score >= 80:
        return "320-480"
    elif lock_in_score >= 60:
        return "160-320"
    elif lock_in_score >= 40:
        return "80-160"
    else:
        return "40-80"


def generate_all_playbooks():
    """Generate migration playbooks for all tracked providers."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    all_playbooks = []
    for provider in PROVIDER_STANDARDS:
        playbook = generate_escape_plan(provider)
        all_playbooks.append(playbook)
        
        # Save individual playbook
        provider_file = OUTPUT_DIR / f"{provider}_migration_playbook.json"
        with open(provider_file, "w") as f:
            json.dump(playbook, f, indent=2, default=str)
        print(f"Generated: {provider_file}")
    
    # Generate comparative summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_providers": len(all_playbooks),
        "provider_rankings": sorted(
            [{"provider": p["provider"], "lock_in_score": p["lock_in_score"],
              "estimated_days": p["total_estimated_days"]} for p in all_playbooks],
            key=lambda x: x["lock_in_score"], reverse=True
        ),
        "easiest_migration": min(all_playbooks, key=lambda x: x["lock_in_score"])["provider"],
        "hardest_migration": max(all_playbooks, key=lambda x: x["lock_in_score"])["provider"],
    }
    
    summary_file = OUTPUT_DIR / "migration_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Summary: {summary_file}")
    
    return all_playbooks


if __name__ == "__main__":
    playbooks = generate_all_playbooks()
    print(f"\nGenerated {len(playbooks)} migration playbooks")
    for pb in playbooks:
        print(f"  {pb['provider']}: lock-in={pb['lock_in_score']}, days={pb['total_estimated_days']}")
