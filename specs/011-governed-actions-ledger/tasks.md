# Tasks: Governed Actions & Decision Ledger (Slice S5 / F10)

**Input**: Design documents from `/specs/011-governed-actions-ledger/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)  
**Authoritative References**: `initial_plan.md` §6.1, §6.2, §5.1, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `.specify/memory/constitution.md`  
**Prerequisites**: Virtualenv active (`FEIOS/.venv/bin/python`), DuckDB hot-state engine, registered OMCP tools.  

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (`[US1]` through `[US6]`), omitted for Setup, Foundational, and Polish phases
- All tasks specify exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure & Domain Schemas)

**Purpose**: Package initialization, domain models, and synthetic test fixtures

- [x] T001 Initialize governance package structure and exports in FEIOS/src/eios/ontology/actions/__init__.py
- [x] T002 [P] Create Pydantic v2 domain schemas (ActionIntentToken, ApprovalRecord, LedgerEntry, ExecutionReceipt, WORMAnchorCheckpoint, DecisionOutcomeRecord, AuditVerificationReport) in FEIOS/src/eios/ontology/actions/models.py
- [x] T003 [P] Configure synthetic governance test fixtures, mock KMS signer, and test helper factories in FEIOS/tests/ontology/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core hot-state storage, JSON Schema contract tests, and cryptographic signing baseline  
**⚠️ CRITICAL**: Must complete before user story implementation begins

- [x] T004 Setup DuckDB analytical DDL schemas (atomic_sequence_ledger, governed_action_intents, simulated_writeback_ledger, worm_anchor_checkpoints, decision_outcomes_ledger) in FEIOS/src/eios/ingestion/hot_state.py
- [x] T005 [P] Implement JSON Schema contract validation tests asserting compliance with action-intent-token.schema.json, ledger-entry.schema.json, execution-receipt.schema.json, worm-anchor-checkpoint.schema.json, and audit-verification-report.schema.json in FEIOS/tests/ontology/test_governance_contracts.py
- [x] T006 [P] Verify Cloud KMS ECDSA P-256 asymmetric signer, RFC 8785 canonical JSON serialization, and DER signature verification in FEIOS/src/eios/ontology/actions/signer.py

**Checkpoint**: Foundation ready - hot state initialized, schemas registered, contract tests active, cryptographic signing primitives verified.

---

## Phase 3: User Story 1 - Atomic Monotonic Sequencer & Cryptographic Hash Chain Ledger (Priority: P1) 🎯 MVP

**Goal**: Stamp every proposal, human approval, and execution event with an upstream atomic, strictly monotonic sequence number and maintain an unbroken SHA-256 cryptographic hash chain linking to a pre-registered genesis anchor  
**Independent Test**: Run `pytest FEIOS/tests/ontology/test_ledger_sequencer.py`; verify sequence numbers increment strictly monotonically (1, 2, 3...) with zero gaps, hash chaining computes $H_i = \text{SHA-256}(H_{i-1} \parallel \text{seq}_i \parallel \text{payload}_i)$, and out-of-order writes or tampered payloads are rejected immediately.

### Tests for User Story 1 (Eval-First) ⚠️
- [x] T007 [P] [US1] Write unit and property tests for strictly monotonic sequence numbers, SHA-256 hash chaining, genesis anchor verification, and sequence gap detection in FEIOS/tests/ontology/test_ledger_sequencer.py

### Implementation for User Story 1
- [x] T008 [US1] Implement thread-safe atomic sequence counter and total serialization coordinator in FEIOS/src/eios/ontology/actions/sequencer.py
- [x] T009 [US1] Implement SHA-256 linear hash chaining calculation linking to registered genesis anchor in FEIOS/src/eios/ontology/actions/sequencer.py
- [x] T010 [US1] Implement sequence integrity validation, duplicate sequence rejection, and predecessor digest verification in FEIOS/src/eios/ontology/actions/sequencer.py
- [x] T011 [US1] Implement HotStateEngine persistence writing serialized entries to atomic_sequence_ledger in FEIOS/src/eios/ontology/actions/sequencer.py

**Checkpoint**: User Story 1 (MVP) fully functional and testable independently; upstream monotonic sequencer operational with tamper-evident cryptographic hash chaining.

---

## Phase 4: User Story 2 - Governed Two-Phase Commit State Machine & Four-Eyes Authorization (Priority: P1)

**Goal**: Enforce a strict two-phase commit protocol for all agent mutation proposals, requiring two distinct authenticated human approvals (Four-Eyes principle) for High-severity actions before write-back is unlocked  
**Independent Test**: Run `pytest FEIOS/tests/ontology/test_action_intents.py` and `pytest FEIOS/tests/ontology/test_action_intents_fast_path.py`; verify High-severity actions require two distinct approvers, single-approver attempts fail, operational actions ($\le \$2,500$) use the policy fast-path, and all state transitions are recorded in the atomic sequencer.

### Tests for User Story 2 (Eval-First) ⚠️
- [x] T012 [P] [US2] Write unit tests for Two-Phase Commit state transitions (PENDING -> APPROVED -> EXECUTED/ABORTED), Four-Eyes dual approval enforcement, single-approver fast-path, single-use nonce validation, and 15-minute expiration in FEIOS/tests/ontology/test_action_intents.py

### Implementation for User Story 2
- [x] T013 [US2] Wire ActionIntentHub to LedgerSequencer so that proposal, approval, rejection, and execution events emit cryptographically chained ledger entries in FEIOS/src/eios/ontology/actions/intent_hub.py
- [x] T014 [US2] Implement Four-Eyes dual approval state machine for High-severity actions (HoldWithdrawal, FreezeAccount, ClawbackCommission, SuspendPartner) enforcing two distinct approvers in FEIOS/src/eios/ontology/actions/intent_hub.py
- [x] T015 [US2] Implement policy fast-path for operational actions (LaunchRetentionPlaybook, AdjustPartnerTier) with financial impact $\le \$2,500.00$ in FEIOS/src/eios/ontology/actions/intent_hub.py
- [x] T016 [US2] Implement single-use nonce replay prevention and 15-minute token expiration rejection with TokenExpiredError in FEIOS/src/eios/ontology/actions/intent_hub.py
- [x] T017 [US2] Implement HotStateEngine persistence saving active tokens into governed_action_intents in FEIOS/src/eios/ontology/actions/intent_hub.py

**Checkpoint**: User Story 2 fully functional; Two-Phase Commit state machine active with strict Four-Eyes governance.

---

## Phase 5: User Story 3 - Simulated Core Write-Back Sink with Chaos Fault Injection (Priority: P2)

**Goal**: Commit approved actions against an isolated Simulated Write-Back Sink that produces realistic operational execution receipts, enforces idempotency deduplication, and handles injected chaos faults cleanly  
**Independent Test**: Run `pytest FEIOS/tests/ontology/test_simulated_sink_chaos.py`; verify commits emit typed ExecutionReceipt objects with external transaction IDs, duplicate submissions return existing receipts, and simulated network timeouts transition actions to ABORTED with compensation logs.

### Tests for User Story 3 (Eval-First) ⚠️
- [x] T018 [P] [US3] Write unit and chaos fault injection tests for simulated core write-back execution, idempotency key deduplication, and compensation logging in FEIOS/tests/ontology/test_simulated_sink_chaos.py

### Implementation for User Story 3
- [x] T019 [US3] Implement SimulatedWriteBackSink with external transaction ID generation and simulated settlement latency in FEIOS/src/eios/ontology/actions/sink.py
- [x] T020 [US3] Implement idempotency key cache preventing double-booking and returning original receipts on duplicate requests in FEIOS/src/eios/ontology/actions/sink.py
- [x] T021 [US3] Implement configurable Chaos Fault Injection modes (NONE, NETWORK_TIMEOUT, LEDGER_CONFLICT, CORE_REJECTION) transitioning failed transactions to ABORTED in FEIOS/src/eios/ontology/actions/sink.py
- [x] T022 [US3] Implement compensation intent emission and persistence into simulated_writeback_ledger in FEIOS/src/eios/ontology/actions/sink.py
- [x] T023 [US3] Integrate SimulatedWriteBackSink into ActionIntentHub.execute_action() as the sole authorized commit sink in FEIOS/src/eios/ontology/actions/intent_hub.py

**Checkpoint**: User Story 3 operational; isolated core write-back sink handling executions, idempotency, and chaos faults.

---

## Phase 6: User Story 4 - WORM Chain-Head Anchoring & Continuous Cryptographic Audit Walker (Priority: P2)

**Goal**: Periodically anchor the chain-head hash into simulated immutable WORM storage (GCS Object Retention Lock in Compliance Mode) and run a continuous audit walker detecting single-byte tampering or deleted rows with 100% precision  
**Independent Test**: Run `pytest FEIOS/tests/ontology/test_worm_and_audit_walker.py`; verify periodic WORM checkpoints lock root digests, audit walker returns 100% integrity on clean ledgers, and artificial modification of historical bytes or sequence gaps triggers tamper alerts pinpointing exact sequence index $K$.

### Tests for User Story 4 (Eval-First) ⚠️
- [x] T024 [P] [US4] Write unit and adversary simulation tests for WORM anchor creation, continuous hash chain traversal, 100% integrity scores, and single-byte tamper detection in FEIOS/tests/ontology/test_worm_and_audit_walker.py

### Implementation for User Story 4
- [x] T025 [US4] Implement WORMAnchorService creating immutable compliance checkpoints locked into worm_anchor_checkpoints in FEIOS/src/eios/ontology/actions/worm.py
- [x] T026 [US4] Implement ContinuousAuditWalker sequentially traversing ledger entries and recalculating SHA-256 digests in FEIOS/src/eios/ontology/actions/audit.py
- [x] T027 [US4] Implement WORM anchor cross-verification checking that historical chain-head records match anchored root digests in FEIOS/src/eios/ontology/actions/audit.py
- [x] T028 [US4] Implement single-byte payload tampering and sequence gap detection pinpointing corrupted sequence index $K$ and emitting AuditVerificationReport in FEIOS/src/eios/ontology/actions/audit.py

**Checkpoint**: User Story 4 fully functional; WORM compliance lock active and continuous cryptographic audit walker validating ledger integrity.

---

## Phase 7: User Story 5 - Multi-Horizon Decision Outcomes Ledger & AIPW Counterfactual Logging (Priority: P3)

**Goal**: Log agent propensity scores $e(X)$, causal contexts, and human override decisions at proposal time, followed by multi-horizon (30d, 60d, 90d) forward actuals, enabling unbiased offline Doubly Robust AIPW policy recalibration  
**Independent Test**: Run `pytest FEIOS/tests/ontology/test_decision_outcomes_aipw.py`; verify decision outcomes capture propensity scores, manager override flags, and multi-horizon forward metrics without observational confounding.

### Tests for User Story 5 (Eval-First) ⚠️
- [x] T029 [P] [US5] Write unit tests for proposal-time propensity score logging, manager override tracking, forward horizon reconciliation, and Doubly Robust AIPW counterfactual estimation in FEIOS/tests/ontology/test_decision_outcomes_aipw.py

### Implementation for User Story 5
- [x] T030 [US5] Implement DecisionOutcomesStore recording proposal-time propensity scores $e(X)$, causal covariates $X$, and manager override flags in FEIOS/src/eios/ontology/actions/outcomes.py
- [x] T031 [US5] Implement forward horizon reconciliation (30-day, 60-day, 90-day retention and loss metrics) in FEIOS/src/eios/ontology/actions/outcomes.py
- [x] T032 [US5] Implement Doubly Robust AIPW counterfactual estimation function calculating unconfounded treatment effects in FEIOS/src/eios/ontology/actions/outcomes.py
- [x] T033 [US5] Connect ActionIntentHub proposal issuance and human sign-off overrides to DecisionOutcomesStore in FEIOS/src/eios/ontology/actions/intent_hub.py

**Checkpoint**: User Story 5 operational; multi-horizon decision outcomes ledger powering debiased causal inference.

---

## Phase 8: User Story 6 - Canonical OMCP Governance Tools & Conversational Auditor Specialist (Priority: P3)

**Goal**: Expose governance operations via canonical OMCP tools and provide conversational audit inspections through GovernanceAuditorSpecialist with deterministic replay fallback under LLM outages  
**Independent Test**: Run `pytest FEIOS/tests/ontology/test_omcp_governance_tools.py`; verify OMCP tools execute correctly with role enforcement and specialist returns verified status stamped with [REPLAY] badges during simulated outages.

### Tests for User Story 6 (Eval-First) ⚠️
- [x] T034 [P] [US6] Write integration tests for OMCP governance tool handlers, role enforcement, and conversational replay fallback in FEIOS/tests/ontology/test_omcp_governance_tools.py

### Implementation for User Story 6
- [x] T035 [US6] Register canonical OMCP governance tools (propose_action, approve_action, execute_action, get_ledger_audit_status, verify_hash_chain) in FEIOS/src/eios/ontology/omcp/server.py
- [x] T036 [US6] Implement GovernanceAuditorSpecialist handling conversational intent status and ledger health queries in FEIOS/src/eios/conversation/specialists/governance.py
- [x] T037 [US6] Implement deterministic replay fallback stamped with [REPLAY] badges during simulated LLM/gateway outages in FEIOS/src/eios/conversation/specialists/governance.py
- [x] T038 [US6] Register GovernanceAuditorSpecialist in SupervisoryRouter routing intent and audit queries in FEIOS/src/eios/conversation/router.py

**Checkpoint**: User Story 6 complete; OMCP governance tools and conversational auditor specialist active with deterministic fallback.

---

## Phase 9: Polish & Cross-Cutting Integration

**Purpose**: Validation, end-to-end integration, and complete test suite regression verification

- [x] T039 [P] Execute end-to-end quickstart validation scenarios defined in specs/011-governed-actions-ledger/quickstart.md
- [x] T040 [P] Execute full governance test suite in FEIOS/tests/ontology/ asserting >= 80% line and branch coverage
- [x] T041 Run full repository regression test suite ensuring all 2,135 existing tests pass with 0 failures
- [x] T042 Update project documentation, architecture references, and API tables across specs/011-governed-actions-ledger/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion - BLOCKS all user stories.
- **User Story 1 (Phase 3 - MVP)**: Depends on Phase 2 - foundational sequencer prerequisite.
- **User Story 2 (Phase 4)**: Depends on Phase 3 - wires 2PC state machine to the sequencer.
- **User Story 3 (Phase 5)**: Depends on Phase 4 - execution commit connects to simulated write-back sink.
- **User Story 4 (Phase 6)**: Depends on Phase 3 & 5 - WORM anchor locks sequencer chain head; audit walker verifies ledger.
- **User Story 5 (Phase 7)**: Depends on Phase 4 - links proposals and approvals to decision outcomes.
- **User Story 6 (Phase 8)**: Depends on Phases 3, 4, 5, 6 - exposes OMCP tools and conversational interface.
- **Polish (Phase 9)**: Depends on all user stories being complete.

### Parallel Opportunities

- **Phase 1**: Models (T002) and Test Fixtures (T003) can be built in parallel.
- **Phase 2**: Contract Tests (T005) and Signer Verification (T006) can run in parallel.
- **User Story Tests**: Tests (T007, T012, T018, T024, T029, T034) are written before implementation and can run in parallel.
- **Cross-Component Development**: Once Phase 4 (US2) is complete, US3 (Write-Back Sink), US4 (WORM & Audit Walker), and US5 (AIPW Outcomes) can proceed concurrently.

---

## Parallel Example: User Story 1 (MVP)

```bash
# Launch test and models in parallel:
Task T007: "Write unit and property tests in FEIOS/tests/ontology/test_ledger_sequencer.py"
Task T008: "Implement thread-safe atomic sequence counter in FEIOS/src/eios/ontology/actions/sequencer.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001 - T003)
2. Complete Phase 2: Foundational (T004 - T006)
3. Complete Phase 3: User Story 1 (T007 - T011)
4. **STOP and VALIDATE**: Run `pytest FEIOS/tests/ontology/test_ledger_sequencer.py` to confirm atomic sequence numbers, hash chaining, and gap detection work independently.

### Incremental Delivery

1. Setup + Foundational + US1 $\to$ Cryptographic Sequencer MVP ready.
2. Add US2 $\to$ Governed Two-Phase Commit & Four-Eyes state machine operational.
3. Add US3 $\to$ Simulated Write-Back Sink with idempotency and chaos resilience.
4. Add US4 $\to$ WORM compliance lock and continuous audit walker active.
5. Add US5 $\to$ Multi-horizon counterfactuals and Doubly Robust AIPW tracking ready.
6. Add US6 $\to$ Canonical OMCP governance tools and conversational auditor specialist active with `[REPLAY]` fallback.
7. Polish $\to$ Full regression suite verification (all 2,135 tests passing).
