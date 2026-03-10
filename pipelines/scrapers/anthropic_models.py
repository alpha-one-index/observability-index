"""
ObservabilityIndex - Anthropic Models & Pricing Scraper
Fetches model catalog from Anthropic API and maps to published pricing.
"""
import httpx
import os
from datetime import datetime, timezone

ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"

# Published pricing per 1M tokens (input / output) - USD
# Source: https://docs.anthropic.com/en/docs/about-claude/models
ANTHROPIC_PRICING = {
    "claude-sonnet-4-20250514": {"input_per_1m": 3.00, "output_per_1m": 15.00, "context_window": 200000},
    "claude-3-7-sonnet-20250219": {"input_per_1m": 3.00, "output_per_1m": 15.00, "context_window": 200000},
    "claude-3-5-sonnet-20241022": {"input_per_1m": 3.00, "output_per_1m": 15.00, "context_window": 200000},
    "claude-3-5-haiku-20241022": {"input_per_1m": 0.80, "output_per_1m": 4.00, "context_window": 200000},
    "claude-3-opus-20240229": {"input_per_1m": 15.00, "output_per_1m": 75.00, "context_window": 200000},
    "claude-3-haiku-20240307": {"input_per_1m": 0.25, "output_per_1m": 1.25, "context_window": 200000},
}


async def fetch_anthropic() -> list[dict]:
    """Fetch Anthropic model list and merge with pricing data."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    } if api_key else {}

    now = datetime.now(timezone.utc).isoformat()
    records = []

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(ANTHROPIC_MODELS_URL, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        for model in data.get("data", []):
            model_id = model.get("id", "")
            pricing = ANTHROPIC_PRICING.get(model_id)
            if pricing:
                records.append({
                    "timestamp": now,
                    "provider": "anthropic",
                    "model_id": model_id,
                    "display_name": model.get("display_name", ""),
                    "input_cost_per_1m_tokens": pricing["input_per_1m"],
                    "output_cost_per_1m_tokens": pricing["output_per_1m"],
                    "context_window": pricing["context_window"],
                    "created": model.get("created_at", ""),
                    "source": "anthropic_api",
                })
    except Exception:
        # Fallback: emit pricing records without live API validation
        for model_id, pricing in ANTHROPIC_PRICING.items():
            records.append({
                "timestamp": now,
                "provider": "anthropic",
                "model_id": model_id,
                "display_name": model_id,
                "input_cost_per_1m_tokens": pricing["input_per_1m"],
                "output_cost_per_1m_tokens": pricing["output_per_1m"],
                "context_window": pricing["context_window"],
                "created": "",
                "source": "anthropic_published",
            })

    return records
