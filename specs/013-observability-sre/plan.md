# Implementation Plan: Observability, SRE & Telemetry Spine (F12 / Slice S5)

**Branch**: `013-observability-sre` | **Date**: 2026-10-09 | **Spec**: [specs/013-observability-sre/spec.md](spec.md)

**Input**: Feature specification from `specs/013-observability-sre/spec.md`, `initial_plan.md` §3.3 (L5), §10, `docs/engagement_plan.md` §2, §5, `.specify/memory/constitution.md` (Principles I, II, IV, V, VI, VIII).

---

## 1. Summary

Deliver the **Observability, SRE & Telemetry Spine** (`013-observability-sre` / F12 / Slice S5), establishing the production-grade reliability, telemetry, and SRE governance framework for the Enterprise Intelligence Operating System (EIOS).

Adhering strictly to Google SRE Handbook principles and Palantir/QuantumBlack operational doctrine, the module delivers:
1. **Universal Distributed Tracing Spine**: Full OpenTelemetry instrumentation with W3C `traceparent` context propagation and ambient enterprise `correlation_id` injection across Cockpit, OMCP Server, Reasoning Mesh Coordinator, Domain Tools, Hot-State DB, and the Ledger Sequencer.
2. **10-SLO Continuous Monitoring Engine & 28-Day Error Budget Tracker**: Real-time evaluation of all 10 canonical production SLOs (`docs/engagement_plan.md` §2) using an in-memory discrete time-bucket ring buffer. Tracks rolling 28-day error budgets, computes $1\text{h}$, $6\text{h}$, $24\text{h}$ burn rates, and trips automated `FEATURE_FREEZE` release gates upon budget exhaustion ($< 0\%$).
3. **Multi-Window Multi-Burn-Rate SRE Alerting Policies**: Google SRE standard dual-window confirmation alerting ($14.4\times$ over 1 hour $\to$ Page SEV-1; $6\times$ over 6 hours $\to$ Ticket SEV-2), accompanied by Dead-Letter Queue (DLQ) depth monitors, Cloud KMS signing error rate monitors, and SEV-1 cryptographic ledger mismatch alerts.
4. **LLM Gateway Telemetry & Auditor Gate Tracking**: Per-call tracking of prompt template versions, model identifiers, input/output/cached tokens, financial cost calculation (USD), latency distributions, and Constitution Principle I Auditor Gate verification verdicts (`PASSED`, `MASKED`, `REJECTED`).
5. **Service Golden Signals & Unified Health Summary**: Standardized collection of the Four Golden Signals (Traffic, Latency $p50/p90/p95/p99$, Errors, Saturation) across all six core platform services, exposing real-time operational health to the Data Platform & Operations Board.

---

## 2. Technical Context

**Language/Version**: Python 3.11+ (running on Python 3.14.4 in active virtualenv)  
**Primary Dependencies**:
- `opentelemetry-api>=1.45.0` & `opentelemetry-sdk>=1.45.0` (Native tracing, TracerProvider, SpanProcessor, in-memory & OTLP exporters)
- `pydantic>=2.13.5` (Strict domain entity schemas, JSON Schema generation, and validation)
- `jsonschema>=4.26.0` & `referencing` (Contract validation against Draft 2020-12 schemas)
- `fastapi` / `starlette` (Trace context extraction/injection middleware and health endpoints)
- `duckdb>=1.1.0` (Optional local storage of long-term telemetry snapshots)

**Storage**:
- In-memory thread-safe rolling ring buffers for real-time SLI metrics and span capture (sub-millisecond evaluation latency).
- Local structured JSON log exporter for offline test verification and reproducible eval harness assertions.
- Forward-compatible OTLP export to Google Cloud Trace, Cloud Monitoring, and Cloud Logging.

**Testing**:
- `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`.
- Dedicated unit and contract test suites covering trace propagation, SLO evaluation, error budget depletion, burn-rate alerting, LLM token/cost accounting, and golden signal percentiles.

**Target Platform**: Linux Server / macOS / Google Cloud Run containerized workers  
**Performance Goals**:
- Telemetry span creation and context injection overhead: $< 2\,\text{ms}$ per request `[TARGET]`
- Real-time 10-SLO continuous evaluation latency: $< 100\,\text{ms}$ `[TARGET]`
- Catastrophic burn rate ($14.4\times$) alert trigger latency: $< 60\,\text{s}$ from condition confirmation `[TARGET]`
- Rolling latency percentile ($p50/p90/p95/p99$) computation: $< 10\,\text{ms}$ over 1,000 requests `[TARGET]`

**Constraints**:
- **Constitution Principle I**: Zero ungrounded math; Auditor Gate verification verdicts tracked with 100% citation coverage.
- **Constitution Principle II**: Cryptographic ledger mismatches trigger immediate SEV-1 alerts.
- **Constitution Principle IV**: Data product contract breaches and DLQ routing trigger automated SRE alerts and `DEGRADED` health status.
- **Constitution Principle V**: 100% of telemetry spans carry verified `correlation_id` and provenance metadata.
- **Constitution Principle VI**: All models and engines tested against baseline error rates with $\ge 80\%$ coverage before deployment.
- **Constitution Principle VIII**: Telemetry spine operates in memory under simulated outages, never crashing application execution.
- **Open Architectural Decisions**: Preserves `ADR-009` (frontend stack) and `ADR-014` (API transport).

**Scale/Scope**:
- 10 canonical production SLOs, 6 core micro-services, 6 JSON Schema contracts, and 6 end-to-end validation scenarios.

---

## 3. Constitution Check

*GATE: Evaluated against `.specify/memory/constitution.md`.*

- **Principle I (LLMs Never Compute Business Metrics)**: **PASS**. The LLM telemetry engine monitors the Auditor Gate, ensuring 100% of quantitative figures in text turns are verified against deterministic tools, and logging every validation verdict (`PASSED`, `MASKED`, `REJECTED`).
- **Principle II (No Autonomous Write-Back - NON-NEGOTIABLE)**: **PASS**. Ledger verification failures trigger immediate immutable SEV-1 alerts. KMS signing errors and action intent expirations are monitored continuously.
- **Principle III (Honest Uncertainty & Causal-Evidence Gate)**: **PASS**. Causal refuter test outcomes and refuter failures are captured as structured telemetry attributes on scenario evaluation spans.
- **Principle IV (Data as a Product, Ontology-Only Access)**: **PASS**. Contract breaches, null-check dips, and ingestion freshness SLA delays automatically route to the SRE alerting engine and flag data products as `DEGRADED`.
- **Principle V (Provenance & Labelling)**: **PASS**. Every distributed span and metric observation attaches an enterprise `correlation_id`, ensuring 100% traceability across all execution turns.
- **Principle VI (Eval-First, Baselines & Coverage - NON-NEGOTIABLE)**: **PASS**. All telemetry, SLO, and alerting engines are accompanied by comprehensive unit and contract tests with $\ge 80\%$ coverage before implementation.
- **Principle VII (Specialized Agents & Decoupled Pipelines)**: **PASS**. Telemetry spans record parent-child hierarchy across the Arbitrating Coordinator and specialized domain agents.
- **Principle VIII (Deterministic Fallback & Operability)**: **PASS**. The module provides full OpenTelemetry tracing, multi-burn-rate alerts, 28-day error budget tracking, and automated `FEATURE_FREEZE` governance.

---

## 4. Project Structure & Deliverables

### Documentation (`specs/013-observability-sre/`)
```text
specs/013-observability-sre/
├── plan.md                                           # This architectural implementation plan
├── research.md                                       # Phase 0 architectural trade-offs & design decisions
├── data-model.md                                     # Phase 1 Pydantic v2 domain schemas & state transitions
├── quickstart.md                                     # Phase 1 runnable validation scenarios
├── checklists/
│   └── requirements.md                               # Quality requirements checklist
└── contracts/                                        # JSON Schema Draft 2020-12 contracts
    ├── trace-context-span.schema.json
    ├── error-budget-status.schema.json
    ├── sre-alert-event.schema.json
    ├── llm-invocation-telemetry.schema.json
    ├── auditor-gate-telemetry.schema.json
    └── service-golden-signals.schema.json
```

### Source Code (`FEIOS/src/eios/observability/`)
```text
FEIOS/src/eios/observability/
├── __init__.py                                       # Package export root
├── schemas.py                                        # JSON Schema registry & contract validation
├── tracing.py                                        # OpenTelemetry TracerProvider, ContextSpan, & W3C carrier
├── slo_engine.py                                     # 10-SLO continuous evaluation & 28-day error budget ring buffer
├── alerts.py                                         # Google SRE multi-window multi-burn-rate alerting engine
├── llm_telemetry.py                                  # LLM token/cost accounting & Auditor Gate verification telemetry
└── golden_signals.py                                 # Four Golden Signals collector & service health aggregator
```

### Test Suite (`FEIOS/tests/observability/`)
```text
FEIOS/tests/observability/
├── __init__.py                                       # Test package root
├── test_tracing_spine.py                             # Tests for W3C context propagation & correlation ID injection
├── test_slo_engine.py                                # Tests for 10 canonical SLOs & error budget calculations
├── test_error_budget_freeze.py                       # Tests for automated feature-freeze gating upon budget depletion
├── test_burn_rate_alerts.py                          # Tests for multi-window multi-burn-rate SRE alert policies
├── test_llm_auditor_telemetry.py                     # Tests for LLM tokens, cost USD, & Auditor Gate verdicts
├── test_golden_signals.py                            # Tests for Four Golden Signals & percentile distributions
└── test_contracts_validation.py                      # Contract validation for all 6 JSON Schemas
```

---

## 5. Complexity Tracking

*No unjustified architectural violations. All components strictly adhere to Constitution Principles I–VIII and open decisions ADR-009 / ADR-014.*
