# Quickstart Validation Guide: Observability, SRE & Telemetry Spine (013-observability-sre)

**Feature**: Observability, SRE & Telemetry Spine (`013-observability-sre` / F12 / Slice S5)  
**Spec**: [`specs/013-observability-sre/spec.md`](spec.md)  
**Data Model**: [`specs/013-observability-sre/data-model.md`](data-model.md)  
**Contracts**: [`specs/013-observability-sre/contracts/`](contracts/)  
**Status**: Ready for Planning & Implementation  

---

## 1. Prerequisites & Environment Setup

Verify the Python 3.11+ / uv virtual environment and existing feature test baselines:

```bash
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS"
uv run pytest tests/cockpit/ -q
```

---

## 2. End-to-End Validation Scenarios

### Scenario 1: Distributed Tracing Spine & W3C Correlation ID Propagation
**Objective**: Verify that OpenTelemetry spans propagate `trace_id`, `span_id`, and `correlation_id` across service and tool boundaries without context loss.

```bash
uv run pytest tests/observability/test_tracing_spine.py -v
```
- **Expected Outcome**:
  - Emitted spans conform to [`trace-context-span.schema.json`](contracts/trace-context-span.schema.json).
  - W3C `traceparent` carrier correctly injects and extracts across mock HTTP/OMCP boundaries.
  - Ambient `correlation_id` is automatically attached to 100% of generated spans.

---

### Scenario 2: 10-SLO Continuous Monitoring Engine & Error Budget Accounting
**Objective**: Verify real-time evaluation of all 10 production Service Level Objectives (`docs/engagement_plan.md` §2) and 28-day error budget accounting.

```bash
uv run pytest tests/observability/test_slo_engine.py -v
```
- **Expected Outcome**:
  - Evaluates ingestion freshness ($\le 30$s), contract enforcement ($0$ invalid in hot state), metric query ($\le 500$ms), agent turn latency ($\le 3$s / $\le 20$s), alert dossier assembly ($\le 10$s), pre-withdrawal check ($\le 2$s), morning briefing ($99\%$), approval service ($99.5\%$), ledger integrity ($100\%$), and hallucination gate ($0$ unverified claims).
  - Emitted status records conform to [`error-budget-status.schema.json`](contracts/error-budget-status.schema.json).
  - Evaluation latency across all 10 SLOs completes in $< 100$ milliseconds.

---

### Scenario 3: Automated Feature Freeze Gating upon Error Budget Exhaustion
**Objective**: Verify that exhausting a Tier-1 error budget ($< 0\%$) automatically trips the release gate into `FEATURE_FREEZE` mode.

```bash
uv run pytest tests/observability/test_error_budget_freeze.py -v
```
- **Expected Outcome**:
  - When error events deplete remaining budget $\le 0\%$, service transitions into `FEATURE_FREEZE`.
  - Non-critical release actions are blocked; urgent hotfixes require dual human authorization.
  - Recovery above $0\%$ restores operational status to `HEALTHY` or `WARNING`.

---

### Scenario 4: Google SRE Multi-Window Multi-Burn-Rate Alerting Policies
**Objective**: Verify that high-burn rate failures trigger immediate SEV-1 pager alerts while transient spikes suppress false alarms.

```bash
uv run pytest tests/observability/test_burn_rate_alerts.py -v
```
- **Expected Outcome**:
  - $14.4\times$ burn rate over 1 hour generates a `PAGE_CRITICAL_SEV1` alert within 60 seconds.
  - $6\times$ burn rate over 6 hours generates a `TICKET_HIGH_SEV2` alert.
  - Brief 30-second error spikes do not fire long-window pager alerts.
  - Emitted alert notifications conform to [`sre-alert-event.schema.json`](contracts/sre-alert-event.schema.json).

---

### Scenario 5: LLM Gateway Token, Cost & Auditor Gate Telemetry
**Objective**: Verify granular tracking of language model token consumption, dollar cost accounting, and Constitution Principle I auditor verification verdicts.

```bash
uv run pytest tests/observability/test_llm_auditor_telemetry.py -v
```
- **Expected Outcome**:
  - Telemetry captures prompt ID, model ID, prompt/completion/cached tokens, latency, and USD cost conforming to [`llm-invocation-telemetry.schema.json`](contracts/llm-invocation-telemetry.schema.json).
  - Auditor Gate records verification verdicts (`PASSED`, `MASKED`, `REJECTED`) and metric citation references conforming to [`auditor-gate-telemetry.schema.json`](contracts/auditor-gate-telemetry.schema.json).

---

### Scenario 6: Service Golden Signals & Platform Health Summary
**Objective**: Verify export of Four Golden Signals (Latency, Traffic, Errors, Saturation) across all six core platform services.

```bash
uv run pytest tests/observability/test_golden_signals.py -v
```
- **Expected Outcome**:
  - Core services export throughput, rolling $p50/p90/p95/p99$ latency distributions, error rate, and saturation.
  - Saturation exceeding $85\%$ raises warning status.
  - Health records conform to [`service-golden-signals.schema.json`](contracts/service-golden-signals.schema.json).
