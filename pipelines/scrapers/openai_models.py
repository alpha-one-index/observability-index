"""
ObservabilityIndex - OpenAI Models & Pricing Scraper
Fetches model list from OpenAI API and maps to published pricing.
"""
import httpx
import os
from datetime import datetime, timezone

OPENAI_MODELS_URL = "https://api.openai.com/v1/models"

# Published pricing per 1M tokens (input / output) - USD
# Source: https://openai.com/api/pricing/
OPENAI_PRICING = {
    "gpt-4o": {"input_per_1m": 2.50, "output_per_1m": 10.00, "context_window": 128000},
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60, "context_window": 128000},
    "gpt-4-turbo": {"input_per_1m": 10.00, "output_per_1m": 30.00, "context_window": 128000},
    "gpt-4": {"input_per_1m": 30.00, "output_per_1m": 60.00, "context_window": 8192},
    "gpt-3.5-turbo": {"input_per_1m": 0.50, "output_per_1m": 1.50, "context_window": 16385},
    "o1": {"input_per_1m": 15.00, "output_per_1m": 60.00, "context_window": 200000},
    "o1-mini": {"input_per_1m": 3.00, "output_per_1m": 12.00, "context_window": 128000},
    "o1-pro": {"input_per_1m": 150.00, "output_per_1m": 600.00, "context_window": 200000},
    "o3-mini": {"input_per_1m": 1.10, "output_per_1m": 4.40, "context_window": 200000},
}


async def fetch_openai() -> list[dict]:
    """Fetch OpenAI model list and merge with pricing data."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    now = datetime.now(timezone.utc).isoformat()
    records = []

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(OPENAI_MODELS_URL, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    for model in data.get("data", []):
        model_id = model.get("id", "")
        # Match to pricing table
        pricing = None
        for key in OPENAI_PRICING:
            if model_id == key or model_id.startswith(key + "-"):
                pricing = OPENAI_PRICING[key]
                break

        if pricing:
            records.append({
                "timestamp": now,
                "provider": "openai",
                "model_id": model_id,
                "model_family": key,
                "input_cost_per_1m_tokens": pricing["input_per_1m"],
                "output_cost_per_1m_tokens": pricing["output_per_1m"],
                "context_window": pricing["context_window"],
                "owned_by": model.get("owned_by", ""),
                "created": model.get("created", ""),
                "source": "openai_api",
            })

    return records
