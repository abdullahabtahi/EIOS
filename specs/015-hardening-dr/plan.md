# Implementation Plan: Production Hardening, Chaos Engineering, Soak Testing & Automated Disaster Recovery (015-hardening-dr)

**Branch**: `015-hardening-dr` | **Date**: 2026-10-10 | **Spec**: [specs/015-hardening-dr/spec.md](spec.md)  
**Input**: Feature specification from `specs/015-hardening-dr/spec.md`  
**Authoritative References**: `initial_plan.md` §3.1 (L5), §8 (Slice S5), §10, §12 (`F14-hardening-dr`); `docs/engagement_plan.md` §1 (Phase P3), §2, §7, §8; `.specify/memory/constitution.md` (Principles I–VIII)

---

## Summary

This feature delivers simulated enterprise production hardening across the entire EIOS platform (Phase P3 / Slice S5 completion). It establishes a comprehensive Chaos Engineering suite (process crashes, DLQ floods, simulated LLM outages, duplicate action attempts, and ledger bit-flips), an automated Disaster Recovery (DR) and cold-site failover drill (proving RPO $\le$ 15 min and RTO $\le$ 2 h with cryptographic SHA-256 chain verification), an accelerated 7-day multi-horizon soak test verifying memory stability and zero SLO error budget exhaustion, active STRIDE threat model mitigations (prompt injection defense, KMS signature validation, Token Vault PII anonymization, Four-Eyes enforcement), and automated execution verification for all 10 production runbooks.

---

## Technical Context

**Language/Version**: Python 3.11+ (running in `FEIOS/` workspace with `uv`)  
**Primary Dependencies**: DuckDB, NetworkX, NumPy, SciPy, Pydantic v2, `jsonschema` (Draft 2020-12), `referencing`, `cryptography`  
**Storage**: DuckDB in-memory hot state, cold Parquet backups, WORM retention locks, and SHA-256 hash chains  
**Testing**: `pytest`, `pytest-cov`, `pytest-xdist`  
**Target Platform**: Linux server / macOS container runtime  
**Project Type**: Python core domain package (`eios.hardening`) and canonical OMCP tool integration (`eios.ontology.omcp.server`)  
**Performance Goals**:
- Crash recovery warm-start in $< 5.0$ seconds.
- Clean-site DR restore simulation in $< 30$ seconds (verifying RPO $\le$ 15m and RTO $\le$ 2h).
- Accelerated 7-day operational soak simulation execution in $< 10$ seconds with memory leak rate $\approx 0$.
- Automated diagnosis and resolution across all 10 production runbooks in $< 5.0$ seconds.  
**Constraints**: Strict adherence to Constitution Principles I–VIII; zero code/comment leaks settling open decisions `ADR-002`, `ADR-003`, `ADR-009`, `ADR-014`.  
**Scale/Scope**: 5 core user stories, 5 JSON Schema contracts, 6 quickstart validation scenarios, $\ge 80\%$ test coverage.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Requirement | Compliance Analysis | Status |
| :--- | :--- | :--- | :---: |
| **I. LLMs Never Compute Metrics** | All numbers must come from deterministic tools | All telemetry, memory growth slopes, RPO/RTO calculations, and recovery metrics are computed deterministically; LLMs never estimate figures. | **PASS** |
| **II. No Autonomous Write-Back** | No agent-callable execute tool; four-eyes for high severity | Verifies that Action Intents require single-use nonces, KMS signatures, and Four-Eyes approvals; rejects unauthorized single-operator executions. | **PASS** |
| **III. Causal-Evidence Gate** | Confidence interval excludes zero, placebo refuters pass | Hardening preserves all causal estimation gates; automated drills reject spurious effects. | **PASS** |
| **IV. Data as Product / OMCP** | Access via governed OMCP, schema enforcement | Ingestion routes schema violations to DLQ; hardening status and DR drill proofs are surfaced via canonical OMCP tools with JSON Schema contract enforcement. | **PASS** |
| **V. Provenance & Labelling** | All claims carry source provenance | All drill reports, soak telemetry, and runbook execution proofs include cryptographic SHA-256 digests and execution timestamps. | **PASS** |
| **VI. Eval-First, Baselines** | Tests written before code, $\ge 80\%$ coverage | TDD red-green-refactor workflow; Red-Line security tests RL-1..RL-7 strictly blocking; $\ge 80\%$ coverage enforced. | **PASS** |
| **VII. Decoupled Pipelines** | Structural models computed offline; no God Agent | Decoupled background execution for DR and soak simulation; interactive turns remain low-latency. | **PASS** |
| **VIII. Deterministic Fallback** | Outages must degrade to cached output with replay badge | Explicitly tested under Chaos Scenario 3 & Runbook 3: LLM outages seamlessly trigger cached briefing replay mode with `accent_replay: #b45309`. | **PASS** |
| **Open Decisions Protected** | ADR-002, ADR-003, ADR-009, ADR-014 stay open | Technology-agnostic domain interfaces; no hardcoded commercial model identifiers outside allowed paths. | **PASS** |

---

## Project Structure

### Documentation (this feature)

```text
specs/015-hardening-dr/
├── spec.md              # Feature specification
├── plan.md              # This implementation plan
├── research.md          # Technical research & architectural decisions (Phase 0)
├── data-model.md        # Domain entities, Pydantic v2 models, state transitions (Phase 1)
├── quickstart.md        # 6 runnable validation scenarios (Phase 1)
├── contracts/           # Draft 2020-12 JSON Schema contracts (Phase 1)
│   ├── chaos-experiment-record.schema.json
│   ├── disaster-recovery-drill-report.schema.json
│   ├── soak-test-telemetry-report.schema.json
│   ├── security-threat-drill-result.schema.json
│   └── runbook-execution-proof.schema.json
├── checklists/          # Quality validation checklists
│   └── requirements.md
└── tasks.md             # Implementation tasks (Phase 2, via /speckit-tasks)
```

### Source Code Layout

```text
FEIOS/
├── src/
│   └── eios/
│       ├── hardening/
│       │   ├── __init__.py           # Package exports and version
│       │   ├── schemas.py            # JSON Schema registry and Draft 2020-12 validators
│       │   ├── models.py             # Pydantic v2 domain schemas (ChaosExperimentRecord, etc.)
│       │   ├── chaos.py              # ChaosEngine & injection hooks (crashes, DLQ, LLM outage, replay)
│       │   ├── dr.py                 # DisasterRecoveryCoordinator (snapshotting, teardown, cold restore)
│       │   ├── soak.py               # AcceleratedSoakTestRunner & memory leak regression detector
│       │   ├── stride.py             # STRIDESecuritySuite (prompt injection, token forgery, PII, 4-eyes)
│       │   └── runbooks.py           # RunbookVerificationEngine (automated triage for Runbooks 1–10)
│       └── ontology/
│           └── omcp/
│               └── server.py         # Wire canonical OMCP tool: get_hardening_drill_status
└── tests/
    └── hardening/
        ├── __init__.py
        ├── test_chaos_injection.py
        ├── test_disaster_recovery.py
        ├── test_soak_runner.py
        ├── test_stride_security.py
        ├── test_runbooks_execution.py
        └── test_contracts_validation.py
```

---

## Complexity Tracking

> *No constitutional violations or unjustified complexity detected.*

| Principle / Gate | Deviation | Justification |
| :--- | :--- | :--- |
| *None* | *None* | Pure Python implementation satisfying Principles I–VIII. |
