# Quickstart Validation Guide: Production Hardening, Chaos & Disaster Recovery (015-hardening-dr)

**Feature**: Production Hardening, Chaos Engineering, Soak Testing & Automated Disaster Recovery (`015-hardening-dr` / Feature F14 / Phase P3 / Slice S5)  
**Spec**: [`specs/015-hardening-dr/spec.md`](spec.md)  
**Data Model**: [`specs/015-hardening-dr/data-model.md`](data-model.md)  
**Contracts**: [`specs/015-hardening-dr/contracts/`](contracts/)  
**Status**: Ready for Planning & Implementation  

---

## 1. Prerequisites & Environment Setup

Verify the Python 3.11+ / uv virtual environment and existing feature test baselines:

```bash
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS"
PYTHONPATH=src uv run pytest tests/flywheel/ -q
```

---

## 2. End-to-End Validation Scenarios

### Scenario 1: Chaos Injection & Cold-Start Rehydration
**Objective**: Verify that simulated process crashes trigger automatic warm-start rehydration from Tiered Compaction snapshots in $< 5$ seconds.

```bash
PYTHONPATH=src uv run pytest tests/hardening/test_chaos_injection.py -v -k "test_crash_recovery"
```
- **Expected Outcome**:
  - Emitted record conforms to [`chaos-experiment-record.schema.json`](contracts/chaos-experiment-record.schema.json).
  - Memory wipe is detected and full hot state and property graph rehydrate within 5.0 seconds.
  - Zero lost transactions or corrupted records.

---

### Scenario 2: Simulated LLM Outage & Cached Replay Fallback
**Objective**: Verify that simulated LLM provider failures (HTTP 503, 429 quota exhaustion) degrade seamlessly to cached briefing replay mode without unhandled exceptions or blank screens.

```bash
PYTHONPATH=src uv run pytest tests/hardening/test_chaos_injection.py -v -k "test_llm_outage_fallback"
```
- **Expected Outcome**:
  - Reasoner interceptor catches simulated 503 outage.
  - `MorningBriefingGenerator` immediately serves the prior certified briefing stamped with the institutional replay badge (`accent_replay: #b45309`).
  - Zero hallucinated or invented numbers (Principle I & VIII).

---

### Scenario 3: Automated Disaster Recovery Clean-Site Restore & RPO/RTO Audit
**Objective**: Verify automated cold-storage recovery from Parquet snapshots and WORM anchors following complete platform teardown.

```bash
PYTHONPATH=src uv run pytest tests/hardening/test_disaster_recovery.py -v
```
- **Expected Outcome**:
  - Drill report conforms to [`disaster-recovery-drill-report.schema.json`](contracts/disaster-recovery-drill-report.schema.json).
  - Measured Recovery Point Objective (RPO) $\le 15$ minutes.
  - Measured Recovery Time Objective (RTO) $\le 2$ hours (simulated in $< 30$ seconds).
  - 100% of restored ledger records validate against WORM SHA-256 Merkle root hashes.

---

### Scenario 4: Multi-Horizon Accelerated Soak Test & Memory Leak Audit
**Objective**: Verify operational stability, zero memory leaks, and SLO error budget preservation under a simulated 7-day high-throughput workload.

```bash
PYTHONPATH=src uv run pytest tests/hardening/test_soak_runner.py -v
```
- **Expected Outcome**:
  - Telemetry report conforms to [`soak-test-telemetry-report.schema.json`](contracts/soak-test-telemetry-report.schema.json).
  - Memory slope $\beta_{\text{mem}} \le 0.05$ MB per 1,000 events (`is_leak_free == True`).
  - All 10 platform SLOs remain healthy ($\ge 99\%$ compliance, zero error budget exhaustion).
  - $p95$ query latency $\le 500$ ms, pre-withdrawal check latency $\le 2$ s.

---

### Scenario 5: STRIDE Threat Model Mitigations & Red-Line Security Verification
**Objective**: Verify active defenses against prompt injection, token signature forgery, Token Vault PII extraction, and Four-Eyes bypass attempts.

```bash
PYTHONPATH=src uv run pytest tests/hardening/test_stride_security.py -v
```
- **Expected Outcome**:
  - Results conform to [`security-threat-drill-result.schema.json`](contracts/security-threat-drill-result.schema.json).
  - 100% of adversarial prompt injections in partner comms are stripped/neutralized by the Auditor Gate.
  - Forged token signatures and mismatched key IDs (`kid`) are rejected.
  - Client PII is replaced with synthetic surrogate tokens (`tok_id_cluster_<hex16>`).
  - Single-operator execution on high-severity actions is blocked.

---

### Scenario 6: 10 Production Runbooks Automated Execution Drills
**Objective**: Verify automated incident diagnosis and remediation across all 10 production runbooks from `docs/engagement_plan.md` §8.

```bash
PYTHONPATH=src uv run pytest tests/hardening/test_runbooks_execution.py -v
```
- **Expected Outcome**:
  - Each runbook generates a certified [`runbook-execution-proof.schema.json`](contracts/runbook-execution-proof.schema.json).
  - Automated diagnosis isolates the root cause for all 10 scenarios.
  - Remediation actions restore healthy operational status (`resolution_status == "RESOLVED"`).
