#!/usr/bin/env python3
"""Vendor Lock-In Analyzer - Proprietary scoring engine for ObservabilityIndex.

Quantifies vendor lock-in risk by analyzing data portability, API standards
adherence, contract flexibility, migration complexity, and ecosystem
dependency depth for each provider.

This is a proprietary algorithm unique to the ObservabilityIndex.
"""

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path("data")
OUTPUT_DIR = Path("exports")

# Lock-in dimension weights
LOCKIN_WEIGHTS = {
    "data_portability": 0.25,
    "api_standards": 0.20,
    "contract_flexibility": 0.15,
    "migration_complexity": 0.15,
    "ecosystem_dependency": 0.10,
    "format_openness": 0.10,
    "exit_cost": 0.05,
}

# Standards compliance mapping
OPEN_STANDARDS = [
    "opentelemetry", "prometheus", "grafana", "jaeger",
    "otlp", "w3c_trace_context", "openmetrics",
    "cloudevents", "opensearch", "fluentd",
]


def load_enriched_data() -> dict:
    path = DATA_DIR / "enriched" / "enriched_providers.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def score_data_portability(provider_data: dict) -> float:
    indicators = {
        "data_export_api": 20,
        "bulk_export": 15,
        "standard_formats": 15,
        "export_no_fee": 15,
        "full_history_export": 10,
        "real_time_export": 10,
        "schema_documentation": 10,
        "migration_tools": 5,
    }
    score = 0.0
    portability = provider_data.get("portability", {})
    for ind, points in indicators.items():
        if portability.get(ind) or provider_data.get(ind):
            score += points
    return min(score, 100.0)


def score_api_standards(provider_data: dict) -> float:
    supported = provider_data.get("supported_standards", [])
    if isinstance(supported, str):
        supported = [s.strip() for s in supported.split(",")]
    supported_lower = [s.lower() for s in supported]
    matches = sum(1 for std in OPEN_STANDARDS if std in supported_lower)
    if not OPEN_STANDARDS:
        return 50.0
    coverage = matches / len(OPEN_STANDARDS)
    has_rest = provider_data.get("rest_api", False)
    has_graphql = provider_data.get("graphql_api", False)
    has_grpc = provider_data.get("grpc_api", False)
    api_bonus = sum([has_rest * 5, has_graphql * 5, has_grpc * 5])
    return min(round(coverage * 85 + api_bonus, 2), 100.0)


def score_contract_flexibility(provider_data: dict) -> float:
    score = 50.0
    contract = provider_data.get("contract", {})
    if contract.get("month_to_month"):
        score += 20
    if contract.get("no_minimum_commit"):
        score += 15
    if contract.get("cancel_anytime"):
        score += 10
    if contract.get("data_delete_on_cancel"):
        score += 5
    min_term = contract.get("minimum_term_months", 0)
    if min_term > 24:
        score -= 25
    elif min_term > 12:
        score -= 15
    elif min_term > 6:
        score -= 5
    return max(0.0, min(score, 100.0))


def score_migration_complexity(provider_data: dict) -> float:
    score = 70.0
    migration = provider_data.get("migration", {})
    if migration.get("migration_guide"):
        score += 10
    if migration.get("migration_tooling"):
        score += 10
    if migration.get("competitor_import"):
        score += 10
    proprietary_count = len(provider_data.get("proprietary_features", []))
    if proprietary_count > 10:
        score -= 30
    elif proprietary_count > 5:
        score -= 15
    elif proprietary_count > 2:
        score -= 5
    custom_query = provider_data.get("proprietary_query_language", False)
    if custom_query:
        score -= 20
    return max(0.0, min(score, 100.0))


def score_ecosystem_dependency(provider_data: dict) -> float:
    score = 80.0
    deps = provider_data.get("ecosystem_dependencies", [])
    if len(deps) > 8:
        score -= 30
    elif len(deps) > 4:
        score -= 15
    elif len(deps) > 2:
        score -= 5
    if provider_data.get("requires_proprietary_agent"):
        score -= 20
    if provider_data.get("single_cloud_only"):
        score -= 15
    if provider_data.get("multi_cloud"):
        score += 10
    return max(0.0, min(score, 100.0))


def score_format_openness(provider_data: dict) -> float:
    score = 50.0
    formats = provider_data.get("data_formats", [])
    open_formats = ["json", "csv", "parquet", "avro", "protobuf", "yaml"]
    for fmt in formats:
        if fmt.lower() in open_formats:
            score += 8
    if provider_data.get("open_source_sdk"):
        score += 10
    if provider_data.get("documented_schema"):
        score += 10
    return max(0.0, min(score, 100.0))


def score_exit_cost(provider_data: dict) -> float:
    score = 80.0
    costs = provider_data.get("exit_costs", {})
    if costs.get("egress_fee"):
        score -= 20
    if costs.get("early_termination_fee"):
        score -= 25
    if costs.get("data_extraction_fee"):
        score -= 15
    if costs.get("free_exit"):
        score = 95.0
    return max(0.0, min(score, 100.0))


def classify_lockin(score: float) -> dict:
    if score >= 80:
        return {"level": "minimal", "risk": "low", "recommendation": "safe_to_adopt"}
    elif score >= 60:
        return {"level": "moderate", "risk": "medium", "recommendation": "adopt_with_plan"}
    elif score >= 40:
        return {"level": "significant", "risk": "high", "recommendation": "caution"}
    elif score >= 20:
        return {"level": "heavy", "risk": "very_high", "recommendation": "avoid_if_possible"}
    return {"level": "extreme", "risk": "critical", "recommendation": "do_not_adopt"}


def compute_lockin_score(provider: str, provider_data: dict) -> dict:
    sub_scores = {
        "data_portability": score_data_portability(provider_data),
        "api_standards": score_api_standards(provider_data),
        "contract_flexibility": score_contract_flexibility(provider_data),
        "migration_complexity": score_migration_complexity(provider_data),
        "ecosystem_dependency": score_ecosystem_dependency(provider_data),
        "format_openness": score_format_openness(provider_data),
        "exit_cost": score_exit_cost(provider_data),
    }
    composite = sum(sub_scores[k] * LOCKIN_WEIGHTS[k] for k in LOCKIN_WEIGHTS)
    composite = round(composite, 1)
    classification = classify_lockin(composite)
    return {
        "provider": provider,
        "freedom_score": composite,
        "lock_in_classification": classification,
        "sub_scores": {k: round(v, 2) for k, v in sub_scores.items()},
        "portable": composite >= 65,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def run_lockin_analysis() -> dict:
    enriched = load_enriched_data()
    providers = enriched.get("providers", [])
    if isinstance(providers, dict):
        providers = list(providers.values())
    results = []
    for p in providers:
        name = p.get("name", p.get("provider", "unknown"))
        result = compute_lockin_score(name, p)
        results.append(result)
    results.sort(key=lambda x: x["freedom_score"], reverse=True)
    scores = [r["freedom_score"] for r in results]
    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "algorithm": "Vendor Lock-In Analyzer v1.0",
        "weights": LOCKIN_WEIGHTS,
        "open_standards_tracked": OPEN_STANDARDS,
        "providers": results,
        "summary": {
            "total_providers": len(results),
            "portable_count": sum(1 for r in results if r["portable"]),
            "avg_freedom_score": round(statistics.mean(scores), 1) if scores else 0,
            "most_portable": results[0]["provider"] if results else None,
            "most_locked_in": results[-1]["provider"] if results else None,
        },
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "vendor_lockin_report.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Lock-in analyzed for {len(results)} providers")
    print(f"  Written to {out_path}")
    return output


if __name__ == "__main__":
    run_lockin_analysis()
