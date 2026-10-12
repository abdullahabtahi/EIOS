# Implementation Plan: Layer 1 Ingestion Spine & Contract Gateway (F02)

**Branch**: `003-contracts-ingestion` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-contracts-ingestion/spec.md`

---

## Summary

Feature F02 delivers the **Layer 1 Ingestion Spine & Contract Gateway**, establishing the high-throughput, contract-governed operational telemetry backbone for the entire Enterprise Intelligence Operating System (EIOS) per `initial_plan.md` §3.3 (L1), §8 (Slice S0), `docs/data_products_and_omcp.md`, and `docs/engagement_plan.md`.

F02 operationalizes the Palantir Multimodal Data Plane (MMDP) and McKinsey *Rewired* Tier 1 architecture:
- **Dual Ingestion Router (`eios.ingestion.router`)**: Asynchronous Cloud Pub/Sub worker (`google.cloud.pubsub_v1.SubscriberClient`) with client-side flow control and high-performance synchronous FastAPI webhook endpoint (`POST /v1/events/ingest`) delivering sub-50ms acknowledgements (`FR-001`, `FR-002`, `SC-001`).
- **L1 Contract Validation Gate & Zero-Drop DLQ (`eios.ingestion.validator`)**: Strict Pydantic v2 schema enforcement across all 14 Layer 1 data products. Breaching payloads are diverted to Dead-Letter Queue `eios.l1.dlq.v1` with structured Cloud Logging and automatic product health state transition to `DEGRADED`, guaranteeing zero silent drops per Constitution Principle IV (`FR-003`–`FR-007`, `SC-002`).
- **DuckDB In-Memory Hot-State Engine (`eios.ingestion.hot_state`)**: Vectorized in-process OLAP engine (`:memory:eios_hot_state`). Rehydrates sliding operational window baselines from Parquet lakehouse snapshots in $< 3.0\text{s}$ for $\ge 100,000$ records on container cold boot per ADR-012, backed by container readiness probes (`/readyz`) and liveness probes (`/healthz`) (`FR-008`–`FR-012`, `SC-003`).
- **Single Client View (SCV) Entity Resolution with Hub Suppression (`eios.ingestion.entity_resolution`)**: Two-stage hybrid linker combining deterministic key matching (tax ID, phone, email hashes) with probabilistic Fellegi-Sunter record linkage (name Jaro-Winkler, device fingerprints). Enforces a strict Hub Suppression filter (degree $\ge 5$) on shared family devices and office/CGNAT IPs, capping false merges at $\le 0.1\%$ per ADR-008 (`FR-013`–`FR-016`, `SC-004`, `SC-005`).
- **Deterministic PII Pseudonymization Token Vault (`eios.ingestion.vault`)**: Deterministic HMAC-SHA256 surrogate tokenization (`tok_client_<hex16>`) for all `Marking P` fields before hot-state persistence or downstream reasoning exposure (`FR-017`–`FR-019`, `SC-006`).
- **Real-Time Data Quality & SLA Monitor (`eios.ingestion.dq`)**: Tracks end-to-end event freshness lag (p95 $\le 30\text{s}$ SLO), contract breach counters, and null rates across all 14 data products (`GET /v1/dq/status`) and attaches immutable `_lineage.json` manifests to Parquet lakehouse batches (`FR-020`–`FR-024`, `SC-007`).

---

## Technical Context

**Language/Version**: Python 3.11+ / 3.14 (platform standard).

**Primary Dependencies**: `fastapi>=0.142.2`, `pydantic>=2.13.5`, `duckdb>=1.1.0`, `google-cloud-pubsub>=2.19.0`, `pyarrow>=15.0.0`, `polars>=0.20.0`, `uvicorn>=0.54.0`, `httpx>=0.28.1`, `cryptography>=43.0.0`. Tooling: `pytest` with `pytest-cov`, `ruff`, `mypy`. Rationale and alternatives documented in [research.md](./research.md).

**Storage**: In-memory columnar DuckDB (`:memory:eios_hot_state`), local/GCS Parquet partitions (`data/raw/<product>/`), isolated Token Vault table, Dead-Letter Queue (`eios.l1.dlq.v1`). Dataset-level lineage records in `_lineage.json`.

**Testing**: `pytest` covering unit, contract, and integration tiers under `tests/contracts/`; warm-start rehydration benchmarks; contract breach fuzzing; entity resolution hub suppression tests; PII pseudonymization scans; coverage gate $\ge 80\%$ line and branch `[TARGET]`.

**Target Platform**: Google Cloud Run container (`linux/amd64` / `linux/arm64`) and developer workstations (macOS/Linux).

**Project Type**: Reusable core platform package (`eios.ingestion`) and service application (`eios.ingestion.service`).

**Performance Goals**:
- Event ingestion latency p95 is $\le 30\text{ seconds}$ from source event time to queryable hot state `[TARGET]`.
- Webhook receipt response $\le 50\text{ms}$ `[TARGET]`.
- Hot-state rehydration completes in $< 3.0\text{ seconds}$ on container cold boot for $\ge 100,000$ baseline records `[TARGET]`.
- Vectorized hot-state analytical query latency p95 $\le 15\text{ms}$ `[TARGET]`.
- Sustained throughput $\ge 500\text{ events/sec}$ per container instance `[TARGET]`.

**Constraints**:
- Exactly 100% of contract breaches intercepted and routed to DLQ with zero silent dropping (`Principle IV`).
- Zero raw PII in DuckDB hot state or downstream LLM context windows (`Marking P`).
- False merge rate on shared family devices and shared office IPs $\le 0.1\%$ (`Hub Suppression`).
- Streaming path strictly decoupled from batch model training or SCM fitting (`ADR-013`).

**Scale/Scope**: 14 Layer 1 data products, 3 regulatory tenant scopes (`DERIV_MFSA`, `DERIV_LFSA`, `DERIV_VFSC`), ~100,000 baseline records rehydrated on cold boot.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Principle / Constraint | Pre-research | Post-design |
|---|---|---|---|
| **G1** | **I. LLMs never compute business metrics.** Layer 1 provides deterministic, validated hot state and scalar measurements; no LLM is used in ingestion or metric computation. | PASS | PASS: Ingestion, contract checking, and hot state execute purely via deterministic Python, Pydantic, and DuckDB SQL. |
| **G2** | **II. No autonomous write-back.** Layer 1 maintains an append-only ingestion pipeline, immutable Parquet partitions, and DLQ audit trails. No autonomous write-back to core systems exists. | PASS | PASS: Ingestion worker writes to hot state and GCS/BigQuery staging; mutation intents remain isolated in L5. |
| **G3** | **III. Honest uncertainty & Causal Gate.** Layer 1 preserves all raw event timestamps and line-item details needed for statistical refutation and causal estimation. | PASS | PASS: Data products include microsecond timestamps and unbroken lineage hashes. |
| **G4** | **IV. Data as a product, Ontology access.** All 14 datasets have explicit Pydantic contracts; breaches route to DLQ + raise alerts + mark product `DEGRADED`; zero silent drops; PII pseudonymized under Marking P. | PASS | PASS: Validated in `contracts/dlq-envelope.schema.json` and `contracts/l1-data-product-contracts.md`. |
| **G5** | **V. Provenance and labelling.** Every figure carries a tag (`[TARGET]`, `[BRIEF]`, etc.); event batches emit `_lineage.json` manifests tracking source seeds and git commit SHAs. | PASS | PASS: `FR-022`, `data-model.md` §2.6, and `spec.md` labelling regime. |
| **G6** | **VI. Eval-first, anti-circularity (NON-NEGOTIABLE).** Red-first tests, $\ge 80\%$ coverage; entity resolution tested against hard negatives (shared family devices, campus IPs); evaluated on seeded test splits. | PASS | PASS: `test_entity_resolution.py`, `test_breach_injector.py`, and `contracts/entity-resolution-spec.md`. |
| **G7** | **VII. Specialised agents & decoupled pipelines.** Streaming ingestion path is strictly decoupled from batch feature engineering, training, and SCM fitting (ADR-013). | PASS | PASS: Micro-batch queue flushes to DuckDB independently of batch training jobs. |
| **G8** | **VIII. Deterministic fallback & operability.** Sub-3.0s Parquet warm-start on container cold boot (ADR-012); `/readyz` probe blocks traffic until rehydration is complete; fallback to prior snapshot on corruption. | PASS | PASS: `eios.ingestion.hot_state.warm_start` and `research.md` §1. |
| **G9** | **Secrets & Identity.** Write-only IAM for ingestion service account; HMAC salt and vault keys stored in Secret Manager; approver identity from IdP claims. | PASS | PASS: `research.md` §5 and least-privilege IAM policy. |
| **G10** | **Validation at boundaries.** All external webhook inputs and Pub/Sub messages validated against Pydantic models at ingress boundary before memory allocation. | PASS | PASS: `FastAPI` route dependencies and `eios.ingestion.validator`. |
| **G11** | **Open decisions stay open.** Layer 1 does not dictate or depend on LLM model IDs, frontend UI frameworks (ADR-009), or metric engine choices (ADR-003). | PASS | PASS: Pure backend ingestion and hot-state data plane. |
| **G12** | **Red-Line test readiness.** Layer 1 enforces RL-5 (zero PII leakage via Token Vault) and RL-7 (dead-letter queue capture of invalid payloads). | PASS | PASS: `test_pii_vault.py` and `test_dlq.py`. |

Result: 100% PASS on all gates. The Complexity Tracking table is not needed.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-contracts-ingestion/
├── spec.md                     # Feature specification (24 FRs, 8 SCs)
├── plan.md                     # This file (/speckit-plan output)
├── research.md                 # Phase 0 architectural & library decisions
├── data-model.md               # Phase 1 data entities and schemas
├── quickstart.md               # Phase 1 runnable validation scenarios
├── contracts/
│   ├── ingestion-api.json      # OpenAPI 3.1 schema for ingestion & DQ endpoints
│   ├── dlq-envelope.schema.json# JSON Schema for eios.l1.dlq.v1 records
│   ├── entity-resolution-spec.md# Fellegi-Sunter & Hub Suppression specification
│   └── l1-data-product-contracts.md # 14 L1 Data Product schemas & SLAs
├── checklists/
│   └── requirements.md         # Passed quality checklist
└── tasks.md                    # Created by /speckit-tasks (Phase 2)
```

### Source Code (repository root)

```text
FEIOS/
├── src/eios/
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── config.py           # Ingestion configuration, timeouts, batch thresholds
│   │   ├── router.py           # Dual-path router (FastAPI endpoints + Pub/Sub subscriber)
│   │   ├── validator.py        # Pydantic v2 contract enforcement & schema catalog
│   │   ├── dlq.py              # Dead-letter queue builder, publisher, and alerting
│   │   ├── hot_state.py        # DuckDB in-memory engine (:memory:eios_hot_state) & warm-start
│   │   ├── entity_resolution.py# Hybrid SCV linker (Deterministic + Splink/Fellegi-Sunter + Hubs)
│   │   ├── vault.py            # Deterministic HMAC-SHA256 PII Token Vault (Marking P)
│   │   └── dq.py               # Real-time Data Quality & Freshness SLA monitoring board
│   └── contracts/
│       ├── __init__.py
│       ├── base.py             # Base contract model & serialization utilities
│       └── models.py           # Pydantic v2 models for all 14 L1 data products
└── tests/contracts/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures (mock Pub/Sub, Parquet partitions, tokens)
    ├── test_router.py          # Dual ingestion endpoint & micro-batching tests
    ├── test_contract_gate.py   # Strict schema enforcement & null-rate tests
    ├── test_dlq.py             # Zero-drop Dead-Letter Queue & structured logging tests
    ├── test_warm_start.py      # Sub-3s Parquet rehydration benchmark & readiness tests
    ├── test_hot_state.py       # DuckDB analytical query latency & concurrency tests
    ├── test_entity_resolution.py# Single Client View linking & Hub Suppression tests
    ├── test_pii_vault.py       # Tokenization, referential integrity & zero-leakage tests
    └── test_dq_monitor.py      # Freshness SLA calculation & DEGRADED state transition tests
```

---

## Complexity Tracking

| Component | Design Choice | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|---|
| **Hot State** | In-process DuckDB with Parquet warm-start | Sub-millisecond vectorized analytical queries and zero idle cost in serverless Cloud Run | SQLite is row-oriented and slow for OLAP aggregations; Redis adds $40+/mo dedicated infrastructure and lacks SQL |
| **Entity Resolution** | Two-stage hybrid linker with Hub Suppression | Reconciles MT5, Deriv, and DP2P accounts while preventing false merges of families sharing devices | Pure graph connected components collapses hundreds of benign users sharing campus Wi-Fi or family tablets into false fraud rings |
| **PII Tokenization** | Deterministic HMAC-SHA256 Token Vault | Protects client privacy before analytical querying while preserving relational join capability | Random UUID tokens require locking a central lookup table on every event, bottle-necking ingestion throughput |
| **Dead-Letter Queue** | Dedicated `eios.l1.dlq.v1` envelope | Enforces Constitution Principle IV: zero silent dropping with full auditability and replayability | Simple log warnings lose raw payload bytes and prevent automated incident remediation or replay |
