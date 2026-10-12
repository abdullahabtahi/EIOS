# Feature Specification: Production-Grade Convergence & Sovereign Hardening

**Feature Branch**: `019-production-grade-convergence`  
**Created**: 2026-10-11  
**Status**: Ready for Planning  
**Input**: Comprehensive transition from PoC to Sovereign Institutional Production Grade across the four challenge briefs (`churn.md`, `data.md`, `fraud.md`, `monitoring.md`), resolving all architectural gaps identified across Palantir FDE, QuantumBlack Causal AI, Google Cloud SRE, and Institutional Design standards.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Zero Invariant Violations & Architectural Neutrality (Priority: P1)
As a Principal Software Engineer and System Auditor, I need the entire monorepo to pass 100% of its static architectural checks and test suites without vendor SDK leakage or memory API drift, guaranteeing strict neutrality and complete constitutional compliance.
- **Acceptance Scenario**: Running `pytest` produces **zero failures** (`2,373 passed, 0 failed`), and static pattern scanning (`test_adr002.py` and `test_no_hardcoded_llm_literals.py`) reports zero findings.

### User Story 2 - Live Frontend-Backend Wiring & Dynamic API Streaming (Priority: P1)
As an Institutional Risk Operator, I need the Cockpit web application to stream live analytical data and model inferences directly from the underlying Python domain engines and DuckDB Hot State store via FastAPI REST/SSE endpoints, replacing static mock files (`INITIAL_NODES`, `fixtures.ts`).
- **Acceptance Scenario**: When new trades or risk scores are ingested, the Cockpit UI KPI strips, Churn Radar scatter points, 3-tier sub-affiliate tree, and AML triage queue update dynamically via SSE streams within $< 500\text{ms}$ without page reload.

### User Story 3 - Hardware-Accelerated Dynamic Relational Graph (WebGL / Canvas) (Priority: P1)
As an AML Financial Crime Investigator, I need the relational graph to render dynamically on an interactive HTML5 Canvas / WebGL force-directed canvas capable of smoothly visualizing 1,000+ linked accounts and proxy hubs at 60 FPS, replacing the static 5-node SVG mockup.
- **Acceptance Scenario**: When viewing case `ACC-88219`, the canvas renders the true NetworkX topology with interactive pan, zoom, and node selection; toggling the CGNAT proxy suppression filter ($k > 100$) dynamically collapses carrier hubs in $< 100\text{ms}$ without DOM lag.

### User Story 4 - External Cashier Webhook & In-Line Sentinel Interception (Priority: P2)
As a Chief Compliance Officer, I need the system to expose an authenticated external webhook (`/api/v1/webhooks/cashier/withdrawal`) with HMAC SHA-256 signature verification that intercepts withdrawal requests in-line and issues cryptographic pre-settlement holds via `WithdrawalSentinel` before funds leave.
- **Acceptance Scenario**: An incoming payment withdrawal payload is processed within $< 150\text{ms}$; if flagged by `RoundTripDetector` (micro-P&L roundtrip), the webhook responds with `decision: HOLD` and stages an immutable action intent.

### User Story 5 - Google Cloud BigQuery Lakehouse & GCS WORM Sync (Priority: P2)
As a Capital Markets SRE and Compliance Auditor, I need the decision ledger and domain data products to synchronize upstream atomic sequences into BigQuery external tables and GCS retention-locked WORM storage per ADR-007 and ADR-017.
- **Acceptance Scenario**: Staged and approved actions are streamed to BigQuery with strict monotonic sequencing and verifiable SHA-256 hash chains, triggering tamper alert drills on chain breaks.

### User Story 6 - Institutional Operator Ergonomics & Keyboard Triage (Priority: P2)
As a high-volume Compliance Analyst, I need keyboard-first triage navigation (`j`/`k`, `x`, `e`, `f`, `Cmd+K`) and deep-linkable URL state synchronization to clear backlogs at peak velocity and share forensic evidence states.
- **Acceptance Scenario**: An analyst navigates the triage queue using `j`/`k` and triggers holds via `e`; copying the browser URL reproduces the exact active case, graph zoom coordinates, and filter state in a cold browser session in $< 500\text{ms}$.

### User Story 7 - Branch-per-Scenario Ontology Sandboxing & QuantumBlack Drift Surveillance (Priority: P3)
As a Head of Strategy and Lead Data Scientist, I need What-If parametric simulations to run on isolated copy-on-write ontology branches without mutating the canonical live graph, and continuous Population Stability Index (PSI) monitoring tracking feature distribution drift.
- **Acceptance Scenario**: What-If shocks generate an ephemeral branch ID; PSI calculators flag feature drift if login distribution divergence exceeds $\text{PSI} \ge 0.25$.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST pass all 2,373 monorepo unit and contract tests with zero failures.
- **FR-002**: System MUST isolate vendor LLM SDK imports behind the configured gateway adapter layer (ADR-002).
- **FR-003**: System MUST expose FastAPI REST and native SSE streaming endpoints (`fastapi.sse.EventSourceResponse`) for real-time model outputs.
- **FR-004**: Cockpit web prototype MUST consume live backend endpoints, replacing static `INITIAL_NODES` with live model payloads and providing graceful offline `[REPLAY]` fallback.
- **FR-005**: System MUST replace static SVG graph elements with a hardware-accelerated HTML5 Canvas / WebGL force-directed graph renderer capable of displaying 1,000+ nodes at 60 FPS.
- **FR-006**: System MUST expose an authenticated external cashier webhook (`/api/v1/webhooks/cashier/withdrawal`) with HMAC SHA-256 verification and in-line `WithdrawalSentinel` evaluation.
- **FR-007**: System MUST provide an export sync adapter streaming decision ledger records to BigQuery and GCS WORM storage with SHA-256 hash chaining (ADR-007, ADR-017).
- **FR-008**: Cockpit UI MUST support keyboard-driven triage navigation (`j`/`k`, `x`, `e`, `f`) and global command palette search (`Cmd+K`).
- **FR-009**: Cockpit UI MUST synchronize active forensic state (case ID, active tab, graph viewport, CGNAT toggle, shock deltas) into URL query parameters.
- **FR-010**: System MUST enforce a Four-Eyes approval state machine with 15-minute nonces before high-severity actions transition to `COMMITTED`.
- **FR-011**: System MUST support Branch-per-Scenario ontology sandboxing, ensuring What-If simulations execute on ephemeral forks without mutating canonical live state.
- **FR-012**: System MUST compute continuous model drift surveillance metrics (Population Stability Index and Brier calibration scores) over sliding event windows.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Monorepo automated test suite achieves **100.0% pass rate** (2,373 / 2,373 tests passing).
- **SC-002**: Topological graph canvas renders 1,000 nodes and 2,500 edges at a sustained **$\ge 55\text{ FPS}$** during pan, zoom, and dynamic filter toggles.
- **SC-003**: External withdrawal webhook evaluates transactions and returns an in-line `HOLD` or `RELEASE` decision in **under 150 milliseconds**.
- **SC-004**: Operator triage velocity increases: clearing an alert dossier via keyboard shortcuts requires **under 15 seconds** per case.
- **SC-005**: URL forensic deep links reload the exact identical view and graph state in a cold browser session in **under 500 milliseconds**.
- **SC-006**: Decision ledger achieves **zero external sequence divergence** under concurrent approval simulations.
