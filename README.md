# ObservabilityIndex — Live LLMOps Cost & Reliability Benchmark

[![6h Update](https://img.shields.io/badge/updates-every_6h-brightgreen)]()
[![Providers](https://img.shields.io/badge/providers-25%2B-blue)]()
[![License](https://img.shields.io/badge/license-Apache%202.0-orange)]()

> The definitive real-time benchmark for LLM inference — pricing, latency, error rates, and throughput across 25+ providers, updated every 6 hours.

## What Is ObservabilityIndex?

ObservabilityIndex is an **open-core dataset and API** that answers the question every ML team needs answered:

> *"Which LLM provider gives me the best price-to-performance right now — and how reliable are they really?"*

Public pricing pages tell you list price. ObservabilityIndex tells you what actually happens when you call the API:

- 💰 Live inference pricing (per-token, per-request) across all major providers
- ⚡ Real-time latency measurements (P50, P95, P99 time-to-first-token and total)
- 🔴 Error rates and availability tracking by model and endpoint
- 📊 Throughput benchmarks (tokens/sec) under standardized workloads
- 🔄 Rate limit detection and capacity signals

## Data Sources (All Public)

| Source | Data | Frequency |
|--------|------|-----------|
| OpenAI API | GPT-4o/4.1 pricing, latency, errors | Every 6h |
| Anthropic API | Claude 3.5/4 pricing, latency, errors | Every 6h |
| Google Gemini API | Gemini 2.0/2.5 pricing, latency, errors | Every 6h |
| AWS Bedrock | Multi-model inference pricing | Every 6h |
| Azure OpenAI | Regional pricing and availability | Every 6h |
| Together AI | Open-source model hosting pricing | Every 6h |
| Groq | Ultra-low-latency inference benchmarks | Every 6h |
| Live Latency Probes | Real-time TTFT, P95 latency, health status | Every 6h |
| Status Page Monitor | Outage detection across 7+ AI providers | Every 6h |
| Rate Limit Tracker | Live rate-limit headers and capacity signals | Every 6h |

## Schema

All exports follow the [ObservabilityIndex Schema v1](schemas/schema_v1.json):

```json
{
  "timestamp": "2026-03-09T12:00:00Z",
  "provider": "openai",
  "model": "gpt-4o",
  "endpoint": "chat.completions",
  "region": "us-east",
  "price_per_1k_input_tokens": 0.0025,
  "price_per_1k_output_tokens": 0.01,
  "latency_p50_ms": 245,
  "latency_p95_ms": 890,
  "latency_p99_ms": 1450,
  "ttft_ms": 180,
  "throughput_tokens_per_sec": 85.2,
  "error_rate_pct": 0.12,
  "rate_limit_rpm": 10000,
  "available": true,
  "observability_score": null
}
```

> **Note:** `observability_score` (the proprietary composite reliability+cost+performance score) is available in the [paid API/dataset](https://aws.amazon.com/marketplace).

## Exports

| Format | Location | Access |
|--------|----------|--------|
| CSV | `exports/latest.csv` | Free (this repo) |
| Parquet | `exports/latest.parquet` | Free (this repo) |
| JSON API | `api.observabilityindex.com/v1/` | Free tier (100 req/day) |
| Full History + Score | AWS Data Exchange | Paid subscription |

## Methodology

Full methodology is documented in [docs/methodology.md](docs/methodology.md). All source code for data collection is open. The proprietary normalization engine and ObservabilityScore algorithm are closed-source but the inputs and methodology principles are fully disclosed.

## Quick Start

```bash
# Clone and install
git clone https://github.com/alpha-one-index/observability-index.git
cd observability-index
pip install -r requirements.txt

# Run a single collection cycle
python -m pipelines.collect

# Run with enrichment
python -m pipelines.enrich
```

## License

Data collection pipelines: **Apache 2.0** (use freely)

ObservabilityIndex dataset exports: **CC BY 4.0** (cite us)

ObservabilityScore engine: **Proprietary** (available via paid API/AWS DX)

---

*Part of the [Alpha One Index](https://alphaoneindex.com) ecosystem — AI Infrastructure & Security Research Hub*
