"""
ObservabilityIndex - Google Gemini Models & Pricing Scraper
Fetches model catalog from Google Generative AI API.
"""
import httpx
import os
from datetime import datetime, timezone

GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Published pricing per 1M tokens - USD
# Source: https://ai.google.dev/pricing
GEMINI_PRICING = {
    "gemini-2.5-pro": {"input_per_1m": 1.25, "output_per_1m": 10.00, "context_window": 1048576},
    "gemini-2.5-flash": {"input_per_1m": 0.15, "output_per_1m": 0.60, "context_window": 1048576},
    "gemini-2.0-flash": {"input_per_1m": 0.10, "output_per_1m": 0.40, "context_window": 1048576},
    "gemini-1.5-pro": {"input_per_1m": 1.25, "output_per_1m": 5.00, "context_window": 2097152},
    "gemini-1.5-flash": {"input_per_1m": 0.075, "output_per_1m": 0.30, "context_window": 1048576},
}


async def fetch_google() -> list[dict]:
    """Fetch Google Gemini model list from API."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    params = {"key": api_key} if api_key else {}

    now = datetime.now(timezone.utc).isoformat()
    records = []

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(GEMINI_MODELS_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        for model in data.get("models", []):
            name = model.get("name", "").replace("models/", "")
            # Match to pricing
            pricing = None
            for key in GEMINI_PRICING:
                if name.startswith(key):
                    pricing = GEMINI_PRICING[key]
                    break

            if pricing:
                records.append({
                    "timestamp": now,
                    "provider": "google",
                    "model_id": name,
                    "display_name": model.get("displayName", ""),
                    "input_cost_per_1m_tokens": pricing["input_per_1m"],
                    "output_cost_per_1m_tokens": pricing["output_per_1m"],
                    "context_window": model.get("inputTokenLimit", pricing["context_window"]),
                    "output_token_limit": model.get("outputTokenLimit", 0),
                    "source": "google_api",
                })
    except Exception:
        for model_id, pricing in GEMINI_PRICING.items():
            records.append({
                "timestamp": now,
                "provider": "google",
                "model_id": model_id,
                "display_name": model_id,
                "input_cost_per_1m_tokens": pricing["input_per_1m"],
                "output_cost_per_1m_tokens": pricing["output_per_1m"],
                "context_window": pricing["context_window"],
                "output_token_limit": 0,
                "source": "google_published",
            })

    return records
