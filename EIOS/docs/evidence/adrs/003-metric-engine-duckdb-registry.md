# ADR-003: Metric Engine (In-Process DuckDB Semantic Registry)

## Status

Accepted

## Date

2026-10-05

## Context

Principle I (Non-Negotiable) mandates that LLMs never compute business metrics directly; all business numbers must arrive deterministically from the Semantic Metric Layer.
Earlier planning (v2) considered Cube Core as an external metric virtualization engine. However, Spike S-02 analyzed the operational footprint: Cube Core requires a persistent Node.js service, CubeStore/Redis worker tiers, and adds substantial network hop latency and ops overhead, making it incompatible with serverless scale-to-zero Cloud Run environments.

## Options considered

- **Cube Core**: Standalone semantic layer service. Pros: feature-rich web UI and pre-aggregations. Cons: Heavy resource footprint, external Redis/CubeStore dependencies, cold-boot penalties (>10s), complex IAM, high operational cost for scale-to-zero.
- **In-Process DuckDB Semantic Registry (Chosen)**: Lightweight Python-native metric engine evaluating versioned SQL expressions directly against partitioned Parquet snapshots / in-process Arrow tables. Pros: sub-5ms query latency, zero external service dependencies, scale-to-zero native, deterministic query hashing, strict schema validation. Cons: does not have an out-of-the-box UI dashboard (mitigated by custom Cockpit views).
- **Direct BigQuery Queries**: Pushing every KPI evaluation down to BigQuery. Cons: high query latency (1–3s per query), high per-query slot/scan costs, poor responsiveness for interactive agent loops.

## Decision

Adopt the **In-Process DuckDB Semantic Registry** (`DuckDBMetricRegistry`) as the core metric engine. Metrics are defined declaratively with explicit grain, dimensions, filters, SQL aggregate expressions, owner, and versioning. DuckDB executes deterministic aggregations over hot state and Parquet data products.

## Consequences

- Positive: Sub-5ms metric evaluation SLA; zero operational cost at scale-to-zero; zero external worker dependencies.
- Positive: Guaranteed deterministic compliance with Constitution Principle I.
- Negative: Memory capacity bounded by container limits (mitigated by partitioned Parquet pushdown and warm-start snapshotting).

## Evidence

Spike S-02 benchmarks; 100% test coverage in `FEIOS/tests/ontology/test_metric_registry.py` with zero regressions and sub-5ms evaluation latency.

## Revisit when

Data product volume in single-tenant hot state exceeds container memory thresholds (>8 GB RAM), at which point hybrid pushdown to BigQuery or Spanner may be evaluated.
