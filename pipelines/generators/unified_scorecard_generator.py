#!/usr/bin/env python3
"""Unified Scorecard Generator - Wish #2 for VP of Platform Engineering.

Combines ALL scoring engine outputs (reliability, cost drift, compliance,
vendor lock-in, alpha value) into a single per-provider scorecard with
letter grades, trend arrows, and board-ready summary data.

This is the "one dashboard to rule them all" that replaces Gartner PDFs,
biased vendor status pages, and anecdotal Reddit threads.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

EXPORTS_DIR = Path("exports")
OUTPUT_DIR = EXPORTS_DIR / "scorecards"
HISTORY_DIR = EXPORTS_DIR / "scorecard_history"

# Scoring engine report files
SCORING_REPORTS = {
    "reliability": EXPORTS_DIR / "provider_reliability_index.json",
    "cost_drift": EXPORTS_DIR / "cost_drift_report.json",
    "compliance": EXPORTS_DIR / "compliance_risk_report.json",
    "vendor_lockin": EXPORTS_DIR / "vendor_lockin_report.json",
    "alpha_value": EXPORTS_DIR / "alpha_value_scores.json",
}

# Unified scorecard weights (how much each engine matters to overall grade)
UNIFIED_WEIGHTS = {
    "reliability": 0.30,
    "cost_drift": 0.20,
    "compliance": 0.20,
    "vendor_lockin": 0.15,
    "alpha_value": 0.15,
}

# Letter grade thresholds
GRADE_THRESHOLDS = [
    (95, "A+"), (90, "A"), (85, "A-"),
    (80, "B+"), (75, "B"), (70, "B-"),
    (65, "C+"), (60, "C"), (55, "C-"),
    (50, "D+"), (45, "D"), (40, "D-"),
    (0, "F"),
]

# Trend symbols
TREND_SYMBOLS = {
    "improving": "up",
    "stable": "stable",
    "declining": "down",
    "new": "new",
}


def load_report(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def load_previous_scorecards() -> dict:
    latest = HISTORY_DIR / "latest_scorecards.json"
    if latest.exists():
        with open(latest) as f:
            return json.load(f)
    return {}


def get_letter_grade(score: float) -> str:
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def compute_trend(current: float, previous: Optional[float]) -> str:
    if previous is None:
        return "new"
    diff = current - previous
    if diff > 2.0:
        return "improving"
    elif diff < -2.0:
        return "declining"
    return "stable"


def extract_provider_score(report: dict, provider_name: str, score_key: str) -> Optional[float]:
    providers = report.get("providers", report.get("organizations", []))
    if isinstance(providers, list):
        for p in providers:
            name = p.get("provider", p.get("name", p.get("organization", "")))
            if name.lower() == provider_name.lower():
                return p.get(score_key)
    return None


def get_all_provider_names(reports: dict) -> set:
    names = set()
    for engine, report in reports.items():
        providers = report.get("providers", report.get("organizations", []))
        if isinstance(providers, list):
            for p in providers:
                name = p.get("provider", p.get("name", p.get("organization", "")))
                if name:
                    names.add(name)
    return names


def build_provider_scorecard(provider: str, reports: dict, prev_scorecards: dict) -> dict:
    score_keys = {
        "reliability": "pri_score",
        "cost_drift": "drift_score",
        "compliance": "compliance_score",
        "vendor_lockin": "freedom_score",
        "alpha_value": "alpha_score",
    }
    engine_scores = {}
    engine_details = {}
    for engine, report in reports.items():
        key = score_keys.get(engine, "score")
        score = extract_provider_score(report, provider, key)
        if score is not None:
            engine_scores[engine] = score
            providers_list = report.get("providers", [])
            for p in providers_list:
                pname = p.get("provider", p.get("name", ""))
                if pname.lower() == provider.lower():
                    engine_details[engine] = {
                        "score": score,
                        "grade": get_letter_grade(score),
                        "sub_scores": p.get("sub_scores", {}),
                    }
                    break
    if not engine_scores:
        return None
    unified_score = 0.0
    total_weight = 0.0
    for engine, weight in UNIFIED_WEIGHTS.items():
        if engine in engine_scores:
            unified_score += engine_scores[engine] * weight
            total_weight += weight
    if total_weight > 0:
        unified_score = round(unified_score / total_weight * 1.0, 1)
    else:
        unified_score = 0.0
    prev = prev_scorecards.get(provider, {}).get("unified_score")
    trend = compute_trend(unified_score, prev)
    prev_engines = prev_scorecards.get(provider, {}).get("engine_scores", {})
    engine_trends = {}
    for eng, sc in engine_scores.items():
        prev_eng = prev_engines.get(eng)
        engine_trends[eng] = compute_trend(sc, prev_eng)
    strengths = []
    weaknesses = []
    sorted_engines = sorted(engine_scores.items(), key=lambda x: x[1], reverse=True)
    for eng, sc in sorted_engines[:2]:
        if sc >= 70:
            strengths.append({"engine": eng, "score": sc, "grade": get_letter_grade(sc)})
    for eng, sc in sorted_engines[-2:]:
        if sc < 60:
            weaknesses.append({"engine": eng, "score": sc, "grade": get_letter_grade(sc)})
    return {
        "provider": provider,
        "unified_score": unified_score,
        "unified_grade": get_letter_grade(unified_score),
        "trend": trend,
        "trend_symbol": TREND_SYMBOLS.get(trend, "stable"),
        "engine_scores": engine_scores,
        "engine_grades": {e: get_letter_grade(s) for e, s in engine_scores.items()},
        "engine_trends": engine_trends,
        "engine_details": engine_details,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "engines_reporting": len(engine_scores),
        "total_engines": len(UNIFIED_WEIGHTS),
        "data_completeness": round(len(engine_scores) / len(UNIFIED_WEIGHTS) * 100, 1),
        "recommendation": generate_recommendation(unified_score, weaknesses),
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_recommendation(score: float, weaknesses: list) -> str:
    if score >= 85:
        return "strong_candidate"
    elif score >= 70:
        if weaknesses:
            return f"viable_with_caveats_{weaknesses[0]['engine']}"
        return "viable_option"
    elif score >= 55:
        return "proceed_with_caution"
    elif score >= 40:
        return "significant_risks_identified"
    return "not_recommended"


def generate_executive_summary(scorecards: list) -> dict:
    if not scorecards:
        return {}
    scores = [s["unified_score"] for s in scorecards]
    import statistics
    tier_1 = [s for s in scorecards if s["unified_score"] >= 80]
    tier_2 = [s for s in scorecards if 60 <= s["unified_score"] < 80]
    tier_3 = [s for s in scorecards if s["unified_score"] < 60]
    return {
        "total_providers_scored": len(scorecards),
        "average_score": round(statistics.mean(scores), 1),
        "median_score": round(statistics.median(scores), 1),
        "top_provider": scorecards[0]["provider"] if scorecards else None,
        "top_score": scorecards[0]["unified_score"] if scorecards else None,
        "tier_1_recommended": [{"provider": s["provider"], "score": s["unified_score"], "grade": s["unified_grade"]} for s in tier_1],
        "tier_2_viable": [{"provider": s["provider"], "score": s["unified_score"], "grade": s["unified_grade"]} for s in tier_2],
        "tier_3_caution": [{"provider": s["provider"], "score": s["unified_score"], "grade": s["unified_grade"]} for s in tier_3],
        "improving_providers": [s["provider"] for s in scorecards if s["trend"] == "improving"],
        "declining_providers": [s["provider"] for s in scorecards if s["trend"] == "declining"],
    }


def run_scorecard_generation() -> dict:
    reports = {}
    for engine, path in SCORING_REPORTS.items():
        reports[engine] = load_report(path)
    prev_scorecards = load_previous_scorecards()
    all_providers = get_all_provider_names(reports)
    scorecards = []
    for provider in sorted(all_providers):
        card = build_provider_scorecard(provider, reports, prev_scorecards)
        if card:
            scorecards.append(card)
    scorecards.sort(key=lambda x: x["unified_score"], reverse=True)
    executive_summary = generate_executive_summary(scorecards)
    output = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "algorithm": "Unified Scorecard Generator v1.0",
        "weights": UNIFIED_WEIGHTS,
        "grade_scale": GRADE_THRESHOLDS,
        "executive_summary": executive_summary,
        "scorecards": scorecards,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "unified_scorecards.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    history_path = HISTORY_DIR / f"scorecards_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    with open(history_path, "w") as f:
        json.dump({s["provider"]: {"unified_score": s["unified_score"], "engine_scores": s["engine_scores"]} for s in scorecards}, f, indent=2)
    latest_path = HISTORY_DIR / "latest_scorecards.json"
    with open(latest_path, "w") as f:
        json.dump({s["provider"]: {"unified_score": s["unified_score"], "engine_scores": s["engine_scores"]} for s in scorecards}, f, indent=2)
    print(f"  Generated scorecards for {len(scorecards)} providers")
    print(f"  Written to {out_path}")
    return output


if __name__ == "__main__":
    run_scorecard_generation()
