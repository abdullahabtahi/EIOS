# Implementation Plan: Governed Actions & Decision Ledger (Slice S5 / F10)

**Branch**: `011-governed-actions-ledger` | **Date**: 2026-10-08 | **Spec**: [specs/011-governed-actions-ledger/spec.md](spec.md)

**Input**: Feature specification from `specs/011-governed-actions-ledger/spec.md`, `initial_plan.md` §6.1, §6.2, §5.1, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `.specify/memory/constitution.md`.

---

## 1. Summary

Deliver **Governed Actions & Decision Ledger** (Slice S5 / F10), establishing the end-to-end governance, non-autonomous mutation lifecycle, and cryptographic auditability for the Enterprise Intelligence Operating System. Adhering strictly to **Constitution Principle II (No Autonomous Write-Back)**, the system enforces a **Two-Phase Commit State Machine**: AI agents emit non-autonomous mutation proposals (`ActionIntentToken`) signed with Cloud KMS ECDSA P-256 and bound to single-use nonces; mutations strictly require human sign-off before commitment. High-severity actions (`HoldWithdrawal`, `FreezeAccount`, `ClawbackCommission`, `SuspendPartner`) mandate **Four-Eyes Authorization** (two distinct authenticated officers), while operational actions ($\le \$2,500.00$) support a policy-governed fast path.

To eliminate the ordering and gap-detection limitations of distributed streaming data warehouses, an **Upstream Transactional Sequencer (ADR-017)** stamps every proposal, approval, and execution with a strictly monotonic integer counter (`ledger_seq = 1, 2, 3...`) and maintains an unbroken **Cryptographic SHA-256 Hash Chain** ($H_i = \text{SHA-256}(H_{i-1} \parallel \text{ledger\_seq}_i \parallel \text{payload\_digest}_i)$). Periodic **WORM Checkpoint Anchoring** locks the chain head into immutable compliance storage simulating Google Cloud Storage Object Retention Lock in Compliance Mode. A **Continuous Cryptographic Audit Walker** traverses the ledger sequentially, detecting single-byte tampering or sequence gaps with 100% precision. Approved actions commit against a **Simulated Core Write-Back Sink** supporting idempotency deduplication and configurable chaos fault injection (`NETWORK_TIMEOUT`, `LEDGER_CONFLICT`). Finally, a **Multi-Horizon Decision Outcomes Ledger** logs proposal-time propensity scores $e(X)$, causal contexts, manager override flags, and 30/60/90-day forward actuals, powering offline **Doubly Robust AIPW** causal policy recalibration free from observational selection bias.

---

## 2. Technical Context

**Language/Version**: Python 3.11+ (running on Python 3.14.4 in active virtualenv)  
**Primary Dependencies**:
- `cryptography>=42.0.0` (ECDSA NIST P-256 / SECP256R1 asymmetric signing, ASN.1 DER encoding, SHA-256 hashing)
- `duckdb>=1.1.0` (In-process analytical hot state engine for atomic sequence and write-back tables)
- `pydantic>=2.13.5` (Strict domain entity modeling and JSON Schema validation)
- `fastapi` / `starlette` / `mcp` (OMCP governance tool exposure and RPC request validation)

**Storage**:
- DuckDB Hot State (`HotStateEngine`):
  - `atomic_sequence_ledger` (monotonically indexed, cryptographically hash-chained audit events)
  - `governed_action_intents` (active two-phase commit tokens, nonces, and approvals)
  - `simulated_writeback_ledger` (idempotent operational execution receipts and side-effects)
  - `worm_anchor_checkpoints` (immutable compliance retention lock proofs)
  - `decision_outcomes_ledger` (multi-horizon forward counterfactual outcomes and manager overrides)

**Testing**:
- `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`
- Dedicated test suites covering sequencer monotonicity, hash chain tamper detection, four-eyes state transitions, chaos faults, WORM lock compliance, and AIPW counterfactual tracking

**Target Platform**: Linux Server / macOS / Google Cloud Run containerized workers  
**Performance Goals**:
- Upstream Sequencer Monotonic Ingestion: $< 50\,\mu\text{s}$ per transaction `[TARGET]`
- Two-Phase Commit State Machine Evaluation: $< 5\,\text{ms}$ per transition `[TARGET]`
- Simulated Write-Back Execution: $< 100\,\text{ms}$ execution latency `[TARGET]`
- Continuous Cryptographic Audit Traversal: $< 25\,\text{ms}$ per 1,000 entries `[TARGET]`
- Memory Footprint: $< 200\,\text{MB}$ hot-state overhead with sliding-window archival `[TARGET]`

**Constraints**:
- **Constitution Principle I**: Zero LLM math (all ledger sequence numbers, hash digests, financial impacts, and propensity scores computed deterministically) `[TARGET]`
- **Constitution Principle II**: Strict non-autonomous write-back; zero direct agent execution; Four-Eyes dual approval strictly enforced on all High-severity intents `[CONSTITUTION Principle II]`
- **Constitution Principle IV**: Data products consumed exclusively via OMCP tools; raw internal database mutations prohibited
- **Constitution Principle VI**: Unit and integration test suites pass with 100% assertions and zero test regressions against the existing 2,135-test baseline
- **Constitution Principle VIII**: Deterministic replay fallback with `[REPLAY]` badges for all conversational governance status queries during simulated LLM/gateway outages

**Scale/Scope**:
- Full enterprise governance lifecycle spanning 10 canonical action types, 6 event types, 5 HotState DuckDB tables, and 5 external JSON Schema contracts.

---

## 3. Constitution Check

*GATE: Evaluated against `.specify/memory/constitution.md`.*

- **Principle I (LLMs Never Compute Business Metrics)**: **PASS**. All ledger sequence numbers, hash digests, financial budget calculations, and propensity scores are calculated deterministically via standard Python libraries (`cryptography`, `hashlib`, `scipy`). No quantitative figures are generated by LLMs.
- **Principle II (No Autonomous Write-Back - NON-NEGOTIABLE)**: **PASS**. Agents have proposal tools only (`propose_action`). Every proposal is an `ActionIntentToken` signed with Cloud KMS ECDSA P-256, bound to a single-use nonce, and expiring in 15 minutes. High-severity actions require two distinct human approvers before commit. Commitment executes strictly against the isolated `SimulatedWriteBackSink`.
- **Principle III (Honest Uncertainty & Causal Gate)**: **PASS**. Counterfactual tracking records proposing agent propensity score $e(X)$ and high-dimensional causal covariates $X$. Offline Doubly Robust AIPW models calculate treatment effects with refuters and confidence intervals.
- **Principle IV (Data as a Product, Ontology-Only Access)**: **PASS**. Governance operations are exposed via canonical OMCP tools (`propose_action`, `approve_action`, `execute_action`, `get_ledger_audit_status`, `verify_hash_chain`). Raw database access is prohibited.
- **Principle V (Provenance & Labelling)**: **PASS**. Every action intent cites specific evidence references (`evidence_refs`). All metrics carry explicit provenance tags (`[TARGET]`, `[CONSTITUTION Principle II]`, `[BRIEF]`).
- **Principle VI (Eval-First, Baselines & Coverage - NON-NEGOTIABLE)**: **PASS**. Full test suites written before and alongside implementation. Continuous audit walker provides a mathematical baseline verifying 100% integrity score.
- **Principle VII (Specialized Agents & Decoupled Pipelines)**: **PASS**. Governance operations decouple the upstream proposal ingestion from downstream batch AIPW outcome reconciliation. Conversational governance requests route through `GovernanceAuditorSpecialist`.
- **Principle VIII (Deterministic Fallback & Operability)**: **PASS**. Governance audit status queries maintain deterministic replay fallback stamped with `[REPLAY]` badges when LLM services are unavailable.

---

## 4. Project Structure & Deliverables

### Documentation (`specs/011-governed-actions-ledger/`)
```text
specs/011-governed-actions-ledger/
├── plan.md                                           # This architectural implementation plan
├── research.md                                       # Architectural trade-offs & technology selections (Phase 0)
├── data-model.md                                     # Pydantic v2 domain schemas & DuckDB DDL (Phase 1)
├── quickstart.md                                     # Runnable end-to-end validation scenarios (Phase 1)
├── checklists/
│   └── requirements.md                               # Quality requirements checklist (Phase 0)
└── contracts/                                        # JSON Schema interface specifications (Phase 1)
    ├── action-intent-token.schema.json               # Action intent proposal & token schema
    ├── ledger-entry.schema.json                      # Cryptographic ledger entry schema
    ├── execution-receipt.schema.json                 # Simulated write-back receipt schema
    ├── worm-anchor-checkpoint.schema.json            # WORM compliance lock checkpoint schema
    └── audit-verification-report.schema.json         # Continuous audit walker verification report schema
```

### Source Code (`FEIOS/src/eios/`)
```text
FEIOS/src/eios/
├── ontology/
│   ├── actions/
│   │   ├── __init__.py                               # Package exports for governance module
│   │   ├── intent_hub.py                             # Two-phase commit ActionIntentHub & Four-Eyes state machine
│   │   ├── signer.py                                 # Cloud KMS ECDSA P-256 asymmetric signer & verifier
│   │   ├── sequencer.py                              # Upstream atomic monotonic sequencer & SHA-256 hash chainer
│   │   ├── sink.py                                   # Simulated Core Write-Back Sink with chaos fault injection
│   │   ├── worm.py                                   # GCS WORM Compliance Lock anchor service
│   │   ├── audit.py                                  # Continuous Cryptographic Audit Walker
│   │   └── outcomes.py                               # Multi-horizon decision outcomes store & AIPW flywheel tracker
│   └── omcp/
│       └── server.py                                 # OMCP server registering canonical governance tools
├── ingestion/
│   └── hot_state.py                                  # HotStateEngine extended with atomic sequence & WORM tables
└── conversation/
    └── specialists/
        └── governance.py                             # GovernanceAuditorSpecialist with [REPLAY] fallback
```

### Test Suites (`FEIOS/tests/ontology/`)
```text
FEIOS/tests/ontology/
├── test_action_intents.py                            # Two-phase commit proposal and Four-Eyes state machine tests
├── test_action_intents_fast_path.py                  # Single-approver fast-path policy threshold tests
├── test_ledger_sequencer.py                          # Atomic monotonic sequencer and SHA-256 hash chaining tests
├── test_simulated_sink_chaos.py                      # Idempotent write-back and chaos fault injection tests
├── test_worm_and_audit_walker.py                     # WORM checkpoint compliance lock and tamper detection tests
├── test_decision_outcomes_aipw.py                    # Multi-horizon counterfactuals and manager override tests
└── test_omcp_governance_tools.py                     # OMCP tool registration, execution, and replay fallback tests
```

---

## 5. Complexity Tracking

> **No violations recorded.** All architectural decisions adhere directly to Constitution Principles I–VIII.

| Decision / Pattern | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **Upstream Atomic Sequencer** | Guarantees total ordering and gap detection prior to distributed storage | DB auto-increment creates sequence gaps on rollback; BigQuery window functions cannot detect missing rows |
| **Linear SHA-256 Hash Chaining** | Provides tamper-evidence and non-repudiation with $O(1)$ append latency | Merkle trees add branch-rebalancing overhead unnecessary for sequential append-only logs |
| **Simulated Write-Back Sink** | Enables realistic testing of 2PC commits, idempotency, and chaos faults | Mocking raw database writes misses operational timeouts, idempotency keys, and compensation flows |
| **WORM Anchor Checkpoints** | Locks chain head against root database tampering or retroactive re-hashing | Standard database backups or un-locked cloud storage can be rewritten by administrative IAM credentials |

---

## 6. Implementation Phasing Strategy

### Phase 1: Setup & Domain Schemas
- Review and refine Pydantic v2 schemas in `FEIOS/src/eios/ontology/actions/`:
  - `ActionIntentToken`, `ApprovalRecord`, `LedgerEntry`, `ExecutionReceipt`, `WORMAnchorCheckpoint`, `DecisionOutcomeRecord`, `AuditVerificationReport`.
- Extend `HotStateEngine` in `FEIOS/src/eios/ingestion/hot_state.py` with tables:
  - `atomic_sequence_ledger`, `governed_action_intents`, `simulated_writeback_ledger`, `worm_anchor_checkpoints`, and extended `decision_outcomes_ledger`.

### Phase 2: Upstream Atomic Sequencer & Cryptographic Hash Chaining (ADR-017)
- Implement `LedgerSequencer` in `FEIOS/src/eios/ontology/actions/sequencer.py`:
  - Atomic sequence counter `ledger_seq = 1, 2, 3...` with thread-safe concurrency locks.
  - SHA-256 cryptographic chaining: $H_i = \text{SHA-256}(H_{i-1} \parallel \text{seq}_i \parallel \text{digest}_i)$ linking to genesis anchor.
  - Persistence to `atomic_sequence_ledger` in DuckDB hot state.
  - Implement unit tests in `FEIOS/tests/ontology/test_ledger_sequencer.py`.

### Phase 3: Governed Two-Phase Commit State Machine & Four-Eyes Authorization
- Refactor `ActionIntentHub` in `FEIOS/src/eios/ontology/actions/intent_hub.py`:
  - Wire into `LedgerSequencer` to log every proposal, approval, rejection, and execution event.
  - Enforce strict Four-Eyes dual approval for High-severity actions.
  - Enforce single-approver fast-path for operational actions $\le \$2,500.00$.
  - Enforce KMS signature validation and single-use nonces.
  - Update `FEIOS/tests/ontology/test_action_intents.py`.

### Phase 4: Simulated Write-Back Sink with Chaos Fault Injection
- Implement `SimulatedWriteBackSink` in `FEIOS/src/eios/ontology/actions/sink.py`:
  - Idempotency key deduplication cache.
  - Operational transaction emission and side-effects recording in `simulated_writeback_ledger`.
  - Configurable chaos fault injection modes (`NONE`, `NETWORK_TIMEOUT`, `LEDGER_CONFLICT`, `CORE_REJECTION`).
  - Compensation intent emission when transactions abort.
  - Implement unit tests in `FEIOS/tests/ontology/test_simulated_sink_chaos.py`.

### Phase 5: WORM Anchoring & Continuous Cryptographic Audit Walker
- Implement `WORMAnchorService` in `FEIOS/src/eios/ontology/actions/worm.py`:
  - Periodic checkpoint creation locking `chain_head_seq` and `chain_head_hash` into immutable WORM storage.
- Implement `ContinuousAuditWalker` in `FEIOS/src/eios/ontology/actions/audit.py`:
  - Sequential ledger traversal validating hash links, sequence continuity, and WORM anchor proofs.
  - 100% precision single-byte tamper detection pinpointing corrupted sequence index $K$.
  - Implement unit tests in `FEIOS/tests/ontology/test_worm_and_audit_walker.py`.

### Phase 6: Multi-Horizon Decision Outcomes & Doubly Robust AIPW Tracking
- Implement `DecisionOutcomesStore` in `FEIOS/src/eios/ontology/actions/outcomes.py`:
  - Ingestion of proposal-time propensity scores $e(X)$, causal contexts, and manager overrides.
  - Reconciliation of 30-day, 60-day, and 90-day forward actuals.
  - Integration with Churn / Fraud flywheel causal recalibration models.
  - Implement unit tests in `FEIOS/tests/ontology/test_decision_outcomes_aipw.py`.

### Phase 7: OMCP Governance Tools & Conversational Auditor Specialist
- Register canonical governance tools in `FEIOS/src/eios/ontology/omcp/server.py`:
  - `propose_action`, `approve_action`, `execute_action`, `get_ledger_audit_status`, `verify_hash_chain`.
- Implement `GovernanceAuditorSpecialist` in `FEIOS/src/eios/conversation/specialists/governance.py`:
  - Conversational audit inspections.
  - Deterministic replay fallback stamped with `[REPLAY]` badges during LLM gateway outages.
  - Implement integration tests in `FEIOS/tests/ontology/test_omcp_governance_tools.py`.

### Phase 8: Verification & Regression Testing
- Run all feature test suites in `FEIOS/tests/ontology/`.
- Run complete project regression suite across all 2,135+ tests.
