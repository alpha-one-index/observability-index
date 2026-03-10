#!/usr/bin/env python3
"""Live Latency Probe — Real-time API endpoint health & performance measurement.

Unique differentiator: Actually calls provider APIs with minimal tokens to measure
real TTFT (Time to First Token), P95 latency, error rates, and rate-limit headers.
No other public repo does live probing across all major AI providers.
"""

import json
import time
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path

import httpx

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Providers to probe — each needs an API key in env vars
PROVIDERS = {
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "env_key": "OPENAI_API_KEY",
        "payload": {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "stream": True,
        },
        "auth_header": lambda k: {"Authorization": f"Bearer {k}"},
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "env_key": "ANTHROPIC_API_KEY",
        "payload": {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": True,
        },
        "auth_header": lambda k: {"x-api-key": k, "anthropic-version": "2023-06-01"},
    },
    "google": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:streamGenerateContent",
        "env_key": "GOOGLE_API_KEY",
        "payload": {
            "contents": [{"parts": [{"text": "ping"}]}],
            "generationConfig": {"maxOutputTokens": 1},
        },
        "auth_header": lambda k: {},
        "url_key_param": True,
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "env_key": "MISTRAL_API_KEY",
        "payload": {
            "model": "mistral-tiny",
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "stream": True,
        },
        "auth_header": lambda k: {"Authorization": f"Bearer {k}"},
    },
    "cohere": {
        "url": "https://api.cohere.ai/v1/chat",
        "env_key": "COHERE_API_KEY",
        "payload": {
            "message": "ping",
            "max_tokens": 1,
            "stream": True,
        },
        "auth_header": lambda k: {"Authorization": f"Bearer {k}"},
    },
}

NUM_PROBES = 3  # Probes per provider per run
TIMEOUT_SECONDS = 30


def probe_provider(name: str, config: dict) -> dict:
    """Send minimal streaming request and measure real latency metrics."""
    api_key = os.getenv(config["env_key"], "")
    if not api_key:
        return {
            "provider": name,
            "status": "skipped",
            "reason": f"{config['env_key']} not set",
        }

    headers = {"Content-Type": "application/json", **config["auth_header"](api_key)}
    url = config["url"]
    if config.get("url_key_param"):
        url = f"{url}?key={api_key}"

    latencies = []
    ttft_values = []
    errors = []
    rate_limit_info = {}

    for i in range(NUM_PROBES):
        try:
            start = time.perf_counter()
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                with client.stream(
                    "POST", url, headers=headers, json=config["payload"]
                ) as resp:
                    first_byte_time = None
                    for chunk in resp.iter_bytes():
                        if first_byte_time is None:
                            first_byte_time = time.perf_counter() - start
                        break  # We only need first chunk
                    total_time = time.perf_counter() - start

                    # Capture rate-limit headers
                    for h in [
                        "x-ratelimit-remaining-requests",
                        "x-ratelimit-remaining-tokens",
                        "x-ratelimit-limit-requests",
                        "x-ratelimit-reset-requests",
                        "retry-after",
                    ]:
                        val = resp.headers.get(h)
                        if val:
                            rate_limit_info[h] = val

                    if resp.status_code == 200:
                        latencies.append(total_time)
                        if first_byte_time:
                            ttft_values.append(first_byte_time)
                    else:
                        errors.append(
                            {"probe": i, "status": resp.status_code, "body": resp.text[:200]}
                        )
        except Exception as e:
            errors.append({"probe": i, "error": str(e)[:200]})

        if i < NUM_PROBES - 1:
            time.sleep(1)  # Polite delay between probes

    result = {
        "provider": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "probes_sent": NUM_PROBES,
        "successful": len(latencies),
        "errors": errors,
        "rate_limit_headers": rate_limit_info,
    }

    if latencies:
        result["latency_ms"] = {
            "mean": round(statistics.mean(latencies) * 1000, 1),
            "p50": round(sorted(latencies)[len(latencies) // 2] * 1000, 1),
            "p95": round(sorted(latencies)[min(len(latencies) - 1, int(len(latencies) * 0.95))] * 1000, 1),
            "min": round(min(latencies) * 1000, 1),
            "max": round(max(latencies) * 1000, 1),
        }
    if ttft_values:
        result["ttft_ms"] = {
            "mean": round(statistics.mean(ttft_values) * 1000, 1),
            "min": round(min(ttft_values) * 1000, 1),
            "max": round(max(ttft_values) * 1000, 1),
        }

    # Derive health status
    if not latencies:
        result["health"] = "down"
    elif statistics.mean(latencies) > 10:
        result["health"] = "degraded"
    else:
        result["health"] = "healthy"

    return result


def run():
    """Probe all configured providers and write results."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting live latency probes...")
    results = []
    for name, config in PROVIDERS.items():
        print(f"  Probing {name}...")
        result = probe_provider(name, config)
        results.append(result)
        print(f"    -> {result.get('health', 'skipped')}")

    output = {
        "probe_run": datetime.now(timezone.utc).isoformat(),
        "probe_count_per_provider": NUM_PROBES,
        "providers": results,
        "summary": {
            "total_providers": len(results),
            "healthy": sum(1 for r in results if r.get("health") == "healthy"),
            "degraded": sum(1 for r in results if r.get("health") == "degraded"),
            "down": sum(1 for r in results if r.get("health") == "down"),
            "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        },
    }

    out_path = OUTPUT_DIR / "live_latency_probe.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Written to {out_path}")
    return output


if __name__ == "__main__":
    run()
