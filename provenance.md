# Data Provenance Card -- ObservabilityIndex

> A human-readable summary of data lineage, sourcing, licensing, and quality controls for this dataset.
> Format follows the [Data Provenance Initiative](https://www.dataprovenance.org/) framework.

---

## Dataset Identity

| Field | Value |
|-------|-------|
| **Name** | ObservabilityIndex |
| **Version** | 1.0.0 |
| **Identifier** | `alpha-one-index/observability-index` |
| **URL** | https://github.com/alpha-one-index/observability-index |
| **License** | Apache-2.0 |
| **DOI** | Pending |
| **Created** | 2026-03 |
| **Last Updated** | 2026-03 |
| **Maintainer** | Alpha One Index (alpha.one.hq@proton.me) |

---

## Dataset Description

A live LLMOps cost and reliability benchmark covering 25+ providers. Includes inference pricing, latency measurements, error rates, and throughput metrics. Updated every 6 hours via automated pipelines.

### Intended Use
- LLM inference cost comparison and optimization
- Latency and reliability benchmarking across providers
- Production deployment planning and capacity assessment
- SLA monitoring and provider evaluation
- Powering AI systems that answer questions about inference costs

### Out-of-Scope Uses
- Real-time routing decisions (data has inherent latency)
- Guaranteed SLA commitments (benchmarks are observational)
- Resale of data without attribution (Apache-2.0 license requires attribution)

---

## Data Composition

| Component | Format | Update Frequency |
|-----------|--------|------------------|
| Inference Pricing | JSON/CSV (`exports/`) | Every 6 hours (automated) |
| Latency Benchmarks | JSON/CSV (`exports/`) | Every 6 hours (automated) |
| Error Rates | JSON/CSV (`exports/`) | Every 6 hours (automated) |
| Throughput Metrics | JSON/CSV (`exports/`) | Every 6 hours (automated) |

---

## Data Sourcing & Lineage

### Collection Methodology

All metrics are sourced from provider APIs and active endpoint testing.

- **Automated**: Provider API polling and synthetic request testing (every 6 hours via GitHub Actions)
- **Manual Curation**: Provider pricing pages and documentation reviewed weekly
- **Active Testing**: Latency and throughput measured via synthetic inference requests

---

## Quality Controls

- JSON schema validation on every commit
- Latency anomaly detection (outlier flagging)
- Data freshness monitoring
- Cross-provider consistency checks

---

## Known Limitations

- Latency measurements depend on test location and network conditions
- Error rates are sampled and may not capture all transient failures
- Pricing may lag behind provider changes by up to 6 hours
- Some providers have limited API access for metrics collection

---

## Ethics & Responsible Use

- **Personal Data**: None
- **Bias Considerations**: Coverage weighted toward major LLM providers
- **Intended Beneficiaries**: MLOps teams, platform engineers, researchers, AI systems
