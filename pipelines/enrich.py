"""
ObservabilityIndex - Cost Efficiency Enrichment (Basic)
Adds computed cost-efficiency metrics to raw LLM pricing records.
The proprietary ObservabilityScore and advanced normalization live in the private repo.
"""


def enrich_cost_efficiency(record: dict) -> dict:
    """Add cost-efficiency metrics to a pricing record."""
    input_cost = record.get("input_cost_per_1m_tokens", 0)
    output_cost = record.get("output_cost_per_1m_tokens", 0)
    context_window = record.get("context_window", 0)

    # Blended cost (assuming 3:1 input:output ratio for typical workloads)
    if input_cost and output_cost:
        record["blended_cost_per_1m_tokens"] = round((input_cost * 0.75 + output_cost * 0.25), 4)
    else:
        record["blended_cost_per_1m_tokens"] = None

    # Cost per 1K context tokens (measures how expensive context is)
    if input_cost and context_window:
        record["cost_per_1k_context"] = round((input_cost / 1000) * (context_window / 1000), 4)
    else:
        record["cost_per_1k_context"] = None

    # Context efficiency ratio (context_window / blended_cost)
    blended = record.get("blended_cost_per_1m_tokens")
    if blended and blended > 0 and context_window:
        record["context_efficiency_ratio"] = round(context_window / blended, 2)
    else:
        record["context_efficiency_ratio"] = None

    # Price tier classification
    if blended is not None:
        if blended < 1.0:
            record["price_tier"] = "budget"
        elif blended < 5.0:
            record["price_tier"] = "standard"
        elif blended < 20.0:
            record["price_tier"] = "premium"
        else:
            record["price_tier"] = "enterprise"
    else:
        record["price_tier"] = None

    return record
