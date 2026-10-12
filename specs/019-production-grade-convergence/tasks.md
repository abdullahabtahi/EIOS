# Tasks: Production-Grade Convergence & Sovereign Hardening

**Input**: Design documents from `specs/019-production-grade-convergence/`  
**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md)  
**Organization**: Tasks are grouped by priority and user story to enable incremental execution and test validation.

---

## Phase 1: Invariant Remediation & 100% CI Gate (User Story 1 - Priority: P1)

**Purpose**: Fix the 8 failing tests across the monorepo to guarantee 100% test pass rate, strict vendor neutrality (ADR-002), and complete memory manager contract compliance.

- [x] T001 [P1] [US1] Refactor `FEIOS/src/eios/conversation/client.py` to isolate vendor SDK imports behind dynamic loading, eliminating forbidden literals and resolving `test_adr002.py` and `test_no_hardcoded_llm_literals.py`.
- [x] T002 [P1] [US1] Update `SessionMemoryManager` / `ConversationMemoryManager` in `FEIOS/src/eios/conversation/memory.py` to accept `max_tokens` keyword argument, implement `merge_evidence()`, and support pronominal entity resolution (`What is his risk score?` $\to$ `What is John Doe's risk score?`).
- [x] T003 [P1] [US1] Synchronize JSON schema copy directory in `FEIOS/tests/contract/test_schema_copies.py` to eliminate unexpected uncommitted schema warnings.
- [x] T004 [P1] [US1] Execute full monorepo test suite (`pytest`) and verify all 2,373 tests pass with 0 failures and 0 constitutional invariant errors.

---

## Phase 2: Live Backend API Bridge & Native SSE Streaming (User Story 2 - Priority: P1)

**Purpose**: Connect the Python domain engines and DuckDB Hot State store to the Next.js Cockpit via high-performance REST and native SSE streaming endpoints (`fastapi.sse.EventSourceResponse`).

- [x] T005 [P1] [US2] Create FastAPI application in `FEIOS/src/eios/api/app.py` with CORS middleware configured for `http://localhost:3000` and native SSE support.
- [x] T006 [P1] [US2] Expose Partner Churn Radar endpoints (`/api/v1/churn/radar`, `/api/v1/churn/cohorts`) in `FEIOS/src/eios/api/routes_churn.py` returning live 30D VaR, survival hazard probabilities, and SEA cohort anomaly clusters with verified semantic provenance.
- [x] T007 [P1] [US2] Expose Partner Fraud endpoints (`/api/v1/fraud/tree`, `/api/v1/fraud/pairs`) in `FEIOS/src/eios/api/routes_fraud.py` returning the 3-layer sub-affiliate directed graph, mirror trading correlation scores, and clawback exposure.
- [x] T008 [P1] [US2] Expose AML Monitoring endpoints (`/api/v1/aml/triage`, `/api/v1/aml/dossier/{case_id}`) in `FEIOS/src/eios/api/routes_aml.py` returning prioritized investigation dossiers, peer-group baseline comparisons, round-trip micro-P&L sequences, and FinCEN SAR drafts.
- [x] T009 [P1] [US2] Expose SCM Synthesis endpoints (`/api/v1/synthesis/what-if`, `/api/v1/synthesis/briefing`) in `FEIOS/src/eios/api/routes_synthesis.py` executing DoWhy refuter checks and exact 100% Hare-Niemeyer additive driver attribution.
- [x] T010 [P1] [US2] Create `FEIOS/web-prototype/src/components/cockpit/state/api-bridge.ts` in Next.js connecting React state hooks to the FastAPI backend with seamless offline replay fallback (`[REPLAY]` fixtures).

---

## Phase 3: Hardware-Accelerated Dynamic Relational Graph (User Story 3 - Priority: P1)

**Purpose**: Upgrade the AML topological relational graph from a static 5-node SVG mockup to an interactive HTML5 Canvas / WebGL force-directed layout capable of rendering 1,000+ nodes at 60 FPS.

- [x] T011 [P1] [US3] Implement dynamic HTML5 Canvas / WebGL force simulation renderer in `FEIOS/web-prototype/src/components/cockpit/common/topological-graph.tsx`, supporting pan, zoom, velocity physics, and interactive node selection.
- [x] T012 [P1] [US3] Implement dynamic CGNAT proxy hub collapse ($k > 100$) in `topological-graph.tsx`, ensuring carrier gateways are suppressed instantly without visual clutter.
- [x] T013 [P1] [US3] Connect `TopologicalGraphCanvas` to live `/api/v1/aml/dossier/{case_id}/graph` endpoint, rendering real NetworkX mule syndicate topologies.

---

## Phase 4: External Cashier Webhook & In-Line Sentinel Interception (User Story 4 - Priority: P2)

**Purpose**: Expose an authenticated payment gateway webhook intercepting withdrawal requests in-line and executing pre-settlement holds before funds leave.

- [x] T014 [P2] [US4] Implement `/api/v1/webhooks/cashier/withdrawal` in `FEIOS/src/eios/api/routes_webhooks.py` with HMAC SHA-256 signature verification.
- [x] T015 [P2] [US4] Integrate `WithdrawalSentinel` and `RoundTripDetector` into the webhook pipeline, evaluating incoming transactions within $< 150\text{ms}$ and returning instant `HOLD` or `RELEASE` decisions.
- [x] T016 [P2] [US4] Create automated test suite `FEIOS/tests/api/test_cashier_webhook.py` verifying signature rejection, replay attack nonces, and real-time hold execution.

---

## Phase 5: Google Cloud BigQuery & GCS WORM Sync (ADR-007 / ADR-017) (User Story 5 - Priority: P2)

**Purpose**: Stream decision ledger records to BigQuery external tables and GCS retention-locked storage with strict upstream atomic sequence numbers.

- [x] T017 [P2] [US5] Implement BigQuery and GCS sync exporter in `FEIOS/src/eios/ontology/actions/bigquery_sync.py`, streaming finalized ledger records with `ledger_seq`, `prev_hash`, and `new_hash`.
- [x] T018 [P2] [US5] Implement automated tamper-evidence verification drill in `FEIOS/tests/ontology/test_ledger_tamper_drill.py`, validating alert generation if a BigQuery record is modified.

---

## Phase 6: Institutional Operator Ergonomics & Provenance Transparency (User Story 6 - Priority: P2)

**Purpose**: Accelerate operator investigation throughput using keyboard-first navigation, deep-linkable forensic state synchronization, and click-to-verify metric provenance popovers.

- [x] T019 [P2] [US6] Implement `useKeyboardTriage` hook in `FEIOS/web-prototype/src/components/cockpit/shell/use-keyboard-triage.ts` supporting `j`/`k` case movement, `x` selection, `e` pre-settlement hold, and `f` auto-SAR draft.
- [x] T020 [P2] [US6] Implement `useForensicUrlSync` hook in `FEIOS/web-prototype/src/components/cockpit/state/use-forensic-url-sync.ts` bi-directionally binding active case, workstation tab, CGNAT proxy toggle, and slider deltas to URL query parameters.
- [x] T021 [P2] [US6] Integrate global command palette omnibox (`Cmd+K`) in `FEIOS/web-prototype/src/components/cockpit/shell/copilot-command-bar.tsx` with instant fuzzy search across accounts, partners, and metric IDs.
- [x] T022 [P2] [US6] Implement interactive `ProvenancePopover` modal across all numerical KPI values in Cockpit workstations, displaying definition version, as-of timestamp, origin engine, steward, and citation tags (`[BRIEF]`, `[TARGET]`, `[ASSUMPTION]`).

---

## Phase 7: Data Platform Operations Board & DLQ Redrive (User Story 5 / Features 012, 015 - Priority: P2)

**Purpose**: Wire the live Data Platform Operations Board (`operations-board.tsx`) to real-time ingestion telemetry, displaying the 6 Data Product SLAs (< 30s freshness), DLQ quarantine depth, and interactive replay controls.

- [x] T023 [P2] [US5] Expose Data Platform Telemetry endpoints (`/api/v1/ops/telemetry`, `/api/v1/ops/dlq`) in `FEIOS/src/eios/api/routes_ops.py` tracking SLA freshness latencies and quarantined invalid schemas.
- [x] T024 [P2] [US5] Connect `OperationsBoardView` (`operations-board.tsx`) to live telemetry streams, allowing operators to inspect quarantined DLQ payloads and trigger redrive replays.

---

## Phase 8: Branch-per-Scenario Sandboxing & QuantumBlack Drift Surveillance (User Story 7 - Priority: P3)

**Purpose**: Isolate What-If parametric simulations onto copy-on-write ontology branches and monitor model feature stability over time.

- [x] T025 [P3] [US7] Implement `ScenarioSandboxEngine` in `FEIOS/src/eios/ontology/branching/scenario_sandbox.py` allowing operators to fork isolated ontology branches without mutating the canonical live graph.
- [x] T026 [P3] [US7] Implement `DriftSurveillanceEngine` in `FEIOS/src/eios/monitoring/drift_surveillance.py` calculating Population Stability Index (PSI) and Brier calibration scores over sliding trade windows.
- [x] T027 [P3] [US7] Enforce simulated Four-Eyes dual-signoff state machine in `FEIOS/src/eios/ontology/actions/outbox_ledger.py` requiring distinct operator roles before high-severity intents move to `COMMITTED`.

---

## Phase 9: Verification & Red-Line Quality Gate Sign-Off

**Purpose**: Validate end-to-end functionality, generate official Red-Line compliance audit report, and perform live operator walkthrough.

- [x] T028 [P1] [US1..US7] Execute full test suite (`pytest`) and verify 2,373/2,373 passing tests.
- [x] T029 [P1] [US1..US7] Execute formal Red-Line Evaluation Suite (`evals/cli.py --suite redlines`) and generate official tamper-evident compliance audit report (`evals/reports/redline_compliance_report.json`).
- [x] T030 [P1] [US1..US7] Perform end-to-end browser walkthrough at `http://localhost:3000/cockpit`, validating keyboard triage velocity, Canvas graph rendering, live API connectivity, and cashier webhook interception.

