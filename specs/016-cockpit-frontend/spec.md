# Feature Specification: Institutional Operator Cockpit & QuantumBlack Design System Frontend (016-cockpit-frontend)

**Feature Branch**: `016-cockpit-frontend`  
**Created**: 2026-10-10  
**Status**: Ratified  
**Authoritative References**: `initial_plan.md` §7, §3.1 (Invariants I–VIII), `specs/001-platform-foundations` through `specs/015-hardening-dr`, `specs/012-cockpit/spec.md`, `.specify/memory/constitution.md` (Principles I–VIII), `docs/brief/data.md`, `docs/brief/monitoring.md`, `docs/brief/fraud.md`, `docs/brief/churn.md`  
**Input**: User directive: "examine if all the features built from earlier specs was included in the spec/plan. we dont have to ship a disconnected backend-frontend product. review the pass progress to make it production grade, quantumblack + palantir + google cloud engineer rigor quality."

---

## 1. System Vision & Full-Stack Integration Philosophy

The Institutional Operator Cockpit is the single, authoritative Common Operational Picture (COP) for the Enterprise Intelligence Operating System (EIOS). It is **not** an isolated mockup or disconnected prototype. It is a **production-grade, dual-mode full-stack operational workstation** directly connected to the 15 backend subsystems developed across Features 001–015 (`FEIOS/src/eios/`):

1. **Platform Foundations & Security (F001)**: Cloud KMS keyring integration, IdP operator identity claims, clearance levels.
2. **Synthetic Data Foundry (F002)**: Generator seed, git SHA, and dataset hash lineage citations.
3. **Contract-Driven Streaming Ingestion (F003)**: Freshness SLA monitors ($< 30$s), Dead-Letter Queue (DLQ) depth, schema contract validations.
4. **Governed Semantic Metric Layer (F004)**: Deterministic metric queries through DuckDB/BigQuery, 0-hallucination Auditor Gate, 100% provenance transparency.
5. **Evaluation Harness & Red-Line Gates (F005)**: Continuous monitoring of RL-1..RL-7 red-line test gates, naive baselines, and sealed holdout evals.
6. **Decision Intelligence Synthesis & SCM (F006)**: 4-domain Causal DAG, DoWhy refuters (placebo refuter $p > 0.05$, confidence $\ge 0.80$), sub-200ms parametric What-If shock propagation, 100% additive waterfall attribution.
7. **Conversational Analytics Copilot (F007)**: Omnipresent natural language ontology command bar, Auditor Gate rejecting ungrounded numbers.
8. **Multi-Signal Partner Churn Radar (F008)**: $P(\text{churn}) \times \text{VaR}$ scatter, change-point decay indicators, 30-day intervention deadlines, VIP retention playbooks.
9. **Partner Fraud & Mirror Trading Detection (F009)**: Opposite trading pairs ($\ge 85\%$ timing co-occurrence), 3-tier sub-affiliate tree, commission clawback intents.
10. **Client AML Workstation & Graph Topology (F010)**: Priority alert clustering (2,000 to $\le 50$), one-screen evidence dossier, kinetic graph with dynamic CGNAT proxy hub suppression ($k > 100$), near-final SAR draft document.
11. **Governed Action Shelf & Immutable Ledger (F011)**: Two-phase commit Action Intents, Cloud KMS ECDSA P-256 digital signatures, 15m expiration, Four-Eyes dual approval modal, monotonic `ledger_seq`, SHA-256 hash chaining verification bar, WORM anchor proofs.
12. **Cockpit Presentation Engine (F012)**: 5 persona view services (`ExecutiveCockpitService`, `AMLWorkstationService`, `PartnerWorkstationService`, `ComplianceExplorerService`, `DataPlatformOperationsService`), `CockpitSessionManager`, fallback snapshot generator.
13. **Observability, SRE & 10-SLO Error Budgets (F013)**: OpenTelemetry distributed tracing, error budget burndowns across 10 production SLOs, data drift detection (KS test, PSI).
14. **Active Learning Flywheel (F014)**: Closed-loop operator feedback capture (SAR revisions, false-positive typology flags, churn score adjustments) feeding decision outcomes ledger.
15. **Hardening, Disaster Recovery & Chaos (F015)**: DR Runbook execution proofs, automated Cloud KMS key rotation drills, chaos injection indicators, warm-start cache status.

---

## 2. User Scenarios & Testing *(mandatory)*

### User Story 1 - Universal Tripartite COP Shell, QuantumBlack Design System & Copilot Command Bar (Priority: P1) 🎯 MVP

As an **Enterprise Operator (any authenticated role)**,  
I want a unified, high-density, institutional light-mode tripartite operational interface featuring a Left-Rail Triage Inbox, Center Copilot Dossier, Right Kinetic Horizon Canvas, Bottom Governed Action Shelf, and an omnipresent Conversational Copilot Command Bar,  
So that I can monitor real-time operational risks, execute natural language ontology queries guarded by the Auditor Gate, inspect causal narratives, explore relational structures, and stage human-in-the-loop decisions within a single coherent workspace inspired by Palantir Foundry and the QuantumBlack Design System, with zero dark-mode visual fatigue.

**Why this priority**: The universal shell establishes the layout grid, institutional design system tokens, persona role-switching, conversational query bar, streaming communication protocol, and cross-cutting invariants (provenance popovers, Four-Eyes modal, replay badging).

**Independent Test**: Load the operator workstation across desktop viewports (minimum $1440 \times 900$ target); verify institutional light mode (`#ffffff` panel cards, `#f8fafc` canvas ground, slate-navy accents `#0f172a` / `#1e293b`, crisp `#e2e8f0` 1px borders, sharp border radii, zero dark-mode options); verify hovering or clicking any scalar metric renders a deterministic Provenance Popover showing Metric ID, Definition Version, As-Of Timestamp, and Owner Role; verify the Copilot Command Bar executes queries against the ontology while the Metric Auditor Gate blocks any hallucinated or ungrounded number; verify simulated service disruptions trigger immediate `[REPLAY]` or `[CACHED]` fallback badges pursuant to Constitution Principle VIII.

**Acceptance Scenarios**:

1. **Given** an operator navigating to `/cockpit`,  
   **When** the interface initializes,  
   **Then** the shell renders the tripartite grid (Triage Inbox on the left, Copilot Dossier in the center, Kinetic Canvas on the right, Governed Action Shelf anchored at the bottom, and Copilot Command Bar at the top) in institutional light mode with no dark-mode toggle or theme.
2. **Given** any quantitative figure displayed on any card, chart, or dossier narrative,  
   **When** the user clicks or hovers on the metric badge,  
   **Then** an inspector popover renders showing the deterministic metric identifier, ontology semantic definition version, calculation timestamp (`as-of`), calculation engine origin, and steward role, guaranteeing 100% provenance transparency pursuant to Constitution Principle V.
3. **Given** an operator typing a natural language query into the Copilot Command Bar (e.g. "What is our 30-day net deposit turnover for partner P-882?"),  
   **When** the query is evaluated,  
   **Then** the Metric Auditor Gate checks all extracted figures against tool traces; grounded figures pass and highlight with provenance links, while unanchored responses are blocked and returned as "Insufficient data to substantiate figure" pursuant to Principle I and III.
4. **Given** an underlying language model or synthesis engine outage,  
   **When** the operator accesses or refreshes any narrative view,  
   **Then** the interface displays the most recent cached snapshot stamped with an unambiguous amber `[REPLAY]` status badge and the exact generation timestamp, never emitting unverified placeholder text.
5. **Given** an operator switching roles between Executive, AML Investigator, Partner Manager, Compliance Auditor, and Data Operations,  
   **When** the role selector is toggled,  
   **Then** the workspace dynamically updates permissions, filters triage queues, and restructures the center dossier and right canvas to the selected persona without losing uncommitted draft state.

---

### User Story 2 - Executive Decision Cockpit: Morning Briefing & Causal Simulation (Priority: P1)

As a **Chief Executive Officer & Chief Operating Officer**,  
I want an automated morning briefing feed covering 4 business horizons (Competitive, Partner, Client, Financial), an interactive 4-domain causal DAG with DoWhy refuter validation gates, an interactive what-if shock slider, an additive attribution forecast summing to 100%, and strategic trade-off evaluation cards,  
So that I can immediately understand the macroeconomic and operational drivers of revenue and margin changes, test counterfactual strategic responses, and make governed executive decisions backed by causal evidence.

**Why this priority**: C-level executives require synthesized cross-domain explanations of business movements rather than siloed operational dashboards. Providing causal attribution with honest uncertainty guarantees that strategic capital decisions are grounded in mathematically refuted relationships.

**Independent Test**: Navigate to the Executive Decision Cockpit; verify the Morning Briefing feed loads the 4 horizons; verify the causal DAG highlights verified causal edges versus unverified correlations with explicit confidence badges; adjust the What-If Shock Slider (e.g. competitor commission hike $+15\%$, marketing budget shift $-\$50\text{k}$); verify that downstream financial impacts update within 200 ms via parametric propagation, and that attribution components sum to exactly $100\% \pm 0.01\%$.

**Acceptance Scenarios**:

1. **Given** the morning briefing is generated by `ExecutiveCockpitService`,  
   **When** the executive opens the cockpit,  
   **Then** the center pane renders a synthesized executive summary highlighting key insights, emerging operational risks, and market opportunities across Competitive, Partner, Client, and Financial horizons with citations to underlying data products.
2. **Given** the 4-domain causal DAG view,  
   **When** viewing relationships between competitive moves, partner activity, client churn, and financial net revenue,  
   **Then** edges passing refuter checks (placebo refuter $\approx 0$, confidence $\ge 0.80$) render as solid causal vectors, whereas edges failing refutation render as dashed lines labelled "correlation detected; insufficient evidence for causation" pursuant to Constitution Principle III.
3. **Given** the What-If Shock Slider on the scenario simulation card,  
   **When** the executive drags the shock parameter (e.g. "Competitor Payout $+200$ bps"),  
   **Then** the cockpit executes parametric propagation across the cached structural causal model within 200 ms, updating forward 30/60/90-day revenue projections and displaying a waterfall attribution chart whose components sum to exactly 100%.

---

### User Story 3 - AML Investigator Workstation, Relational Graph Canvas & Flywheel Feedback (Priority: P2)

As a **Senior AML Investigator & Compliance Officer**,  
I want an alert triage queue collapsing 2,000 raw weekly alerts into $\le 50$ prioritized high-confidence cases, a one-screen evidence dossier collating 5+ source lookups, a topological graph canvas with dynamic CGNAT hub suppression ($k > 100$), an automated near-final SAR draft composer, pre-withdrawal risk intervention triggers, and Active Learning Flywheel feedback buttons,  
So that I can complete complex money laundering investigations and regulatory filings in seconds rather than days and continuously improve AML typology detection through human-in-the-loop annotations.

**Why this priority**: Anti-money laundering compliance is the highest regulatory risk for brokerage operations. Replacing manual investigations across siloed systems with an integrated dossier, topological graph, and flywheel feedback drastically reduces false-positive triage time and regulatory exposure.

**Independent Test**: Navigate to the AML Investigator Workstation; verify the inbox renders the prioritized top 50 cases; select a case (e.g., round-trip laundering typology); verify the center pane renders the unified dossier with KYC recency, trading turnover, and banking history; verify the right canvas renders the sub-graph with shared device/IP nodes while suppressing high-degree CGNAT hubs; edit the generated SAR narrative and verify 100% of figures carry provenance tool citations; click "Submit Flywheel Feedback" to record human adjustments into the decision outcomes ledger; stage a `HoldWithdrawal` proposal in the bottom governed action shelf.

**Acceptance Scenarios**:

1. **Given** a batch of raw transaction alerts from streaming ingestion (F003),  
   **When** an AML investigator opens the AML Workstation,  
   **Then** the triage queue displays only high-confidence suspicious clusters ranked by priority score, reducing cognitive load from raw alerts down to targeted investigations.
2. **Given** an investigation case selected in the triage inbox,  
   **When** the investigator inspects the center pane,  
   **Then** the dossier presents a single-pane-of-glass timeline collating client KYC approval recency, deposit history, rapid micro-P&L round-trip transactions, and withdrawal requests with statutory citation compliance.
3. **Given** the relational graph canvas,  
   **When** exploring linked accounts sharing hardware identifiers, IPs, or payment methods,  
   **Then** the graph visualizer renders cluster sub-graphs while applying hub suppression to public proxies and CGNAT gateways ($k > 100$), preventing catastrophic false-positive account merges.
4. **Given** an investigator revising a generated SAR narrative or dismissing a false-positive alert,  
   **When** the investigator clicks "Submit Feedback",  
   **Then** the client records the annotation into the Active Learning Flywheel ledger (F014), updating diagnostic calibration metrics.
5. **Given** a high-risk withdrawal attempt requiring urgent intervention,  
   **When** the investigator clicks "Stage Hold Proposal",  
   **Then** the bottom Governed Action Shelf stages a signed `HoldWithdrawal` Action Intent Token in `PENDING` status requiring Four-Eyes authorization pursuant to Constitution Principle II.

---

### User Story 4 - Partner Manager Workstation, Churn Radar & Fraud Ring Canvas (Priority: P2)

As a **Head of Global Partnerships & Affiliate Manager**,  
I want a multi-signal Churn Hazard Radar, systemic cohort risk alerts, a 3-tier sub-affiliate tree visualizer, opposite/mirror trading pair detection cards, proactive retention playbook launchers, and commission clawback staging,  
So that I can identify decaying partner relationships before churn occurs, eliminate illicit arbitrage collusion, and protect affiliate portfolio lifetime value.

**Why this priority**: Affiliate partnerships represent over 60% of brokerage client acquisition volume. Silent partner disengagement and fraudulent mirror trading leak millions annually. Combining churn prediction with fraud ring attribution protects institutional margins.

**Independent Test**: Navigate to the Partner Manager Workstation; verify the churn radar displays partners stratified by Value at Risk $\times P(\text{churn})$; inspect a partner flagged with change-point decay; verify the right canvas visualizes the 3-tier referral hierarchy and opposite trading correlation metrics (timing correlation $\%$, size symmetry, zero-sum ratio); stage a `LaunchRetentionPlaybook` or `FreezePartnerCommission` intent in the action shelf.

**Acceptance Scenarios**:

1. **Given** partner engagement telemetry across behavioural, communication, relationship, and financial signals (F008),  
   **When** the partner manager opens the Partner Workstation,  
   **Then** the triage inbox displays partners categorized into High, Medium, and Low hazard tiers with explicit days-to-churn predictions and Value-at-Risk figures.
2. **Given** partner communication ticket sentiment analysis,  
   **When** viewing a disengaging partner dossier,  
   **Then** the interface displays top driver metrics (e.g. ticket response latency $+40\%$, commission payout drop $-22\%$) and recommends an approved VIP retention playbook.
3. **Given** an illicit mirror trading ring flagged between multiple affiliates (F009),  
   **When** inspecting the fraud integrity view,  
   **Then** the right canvas displays the bidirectional account trading pairs, timing co-occurrence percentage ($\ge 85\%$), and total extracted commission, staging a `ClawbackCommission` intent with full evidentiary lineage.

---

### User Story 5 - Compliance Ledger Explorer, Data Platform Operations & Disaster Recovery Board (Priority: P3)

As a **Compliance Auditor & Data Platform Lead**,  
I want an immutable Decision Ledger explorer with cryptographic SHA-256 hash chain verification status, WORM anchor inspection, Four-Eyes review logs, a Data Product Contract Monitor with dead-letter queue depth, a 10-SLO continuous evaluation board, Red-Line test gate status, and Disaster Recovery Runbook execution proofs,  
So that I can verify institutional regulatory compliance, audit human-in-the-loop decisions, monitor streaming pipeline freshness, verify data quality, and guarantee platform resilience under failure.

**Why this priority**: Institutional regulators and enterprise platform stewards require auditable proof of cryptographic chain continuity, strict pipeline freshness, and documented resilience under operational disaster.

**Independent Test**: Navigate to the Compliance & Audit Explorer; verify the ledger timeline lists sequential records (`ledger_seq = 1, 2, 3...`); verify the SHA-256 chain verification badge displays green (`VALID`); inspect a WORM checkpoint anchor; switch to the Data Platform Operations tab; verify streaming freshness SLA indicators ($< 30$s), contract breach counters, 10-SLO error budget status cards, Red-Line test gates (RL-1..RL-7), and Disaster Recovery runbook proofs.

**Acceptance Scenarios**:

1. **Given** the Decision Ledger explorer (F011),  
   **When** auditing committed operational actions,  
   **Then** the auditor can inspect each record's sequence number, previous hash link, current hash, KMS signing key ID, and dual human approver identity claims.
2. **Given** an active WORM storage checkpoint anchor,  
   **When** the auditor clicks "Verify Chain Continuity",  
   **Then** the client displays the real-time cryptographic verification proof showing 100% chain integrity and WORM compliance mode lock status.
3. **Given** the Data Platform Operations board (F003, F013, F015),  
   **When** viewing streaming ingestion health and platform resilience,  
   **Then** the interface displays live freshness latency across all 6 data products, DLQ quarantine counts, error budget burndown across the 10 production SLOs, RL-1..RL-7 gate statuses, and DR runbook verification proofs (e.g. KMS key rotation, backup restoration).

---

### User Story 6 - Connected Backend Integration Bridge & Dual-Mode Execution (Priority: P1)

As a **Platform Engineer & Operator**,  
I want the Next.js frontend to communicate seamlessly with the Python EIOS presentation engine (`FEIOS/src/eios/cockpit/`) via unified API route handlers, while supporting zero-drift deterministic cached snapshots stamped with amber `[REPLAY]` badges when offline,  
So that the platform operates as a cohesive, production-grade enterprise system with zero disconnected mock components.

**Why this priority**: Prevents building an isolated frontend that drifts from backend domain models, ensuring that every button, chart, and ledger entry reflects live Python domain calculations or verified contract fixtures.

**Independent Test**: Start the Python Cockpit API server (`python -m eios.cockpit.server`); navigate to `/cockpit`; verify live data flows through Next.js API routes; stage and commit an action and verify it appears in the live Python ledger; stop the Python server; verify the frontend gracefully transitions to cached snapshots with amber `[REPLAY]` badges without unhandled exceptions or broken views.

**Acceptance Scenarios**:

1. **Given** the Next.js App Router API handlers (`src/app/api/cockpit/...`),  
   **When** requests are dispatched from the client state manager,  
   **Then** the route handlers forward requests to the Python EIOS cockpit services, validating input and output against `specs/012-cockpit/contracts/` schemas.
2. **Given** an offline or unreachable Python backend,  
   **When** the frontend attempts to fetch workstation state,  
   **Then** the API route transparently falls back to deterministic contract fixtures generated by `eios.cockpit.fallback`, tagging the payload with `is_cached_fallback = true` and rendering amber `[REPLAY]` badges.

---

## 3. Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a tripartite layout architecture consisting of a Left Triage Rail ($300\text{px}$), Center Copilot Dossier ($560\text{px}$), Right Kinetic Analytical Canvas, and Bottom Governed Action Shelf.
- **FR-002**: System MUST enforce high-density Institutional Light Mode inspired by the QuantumBlack Design System (`#ffffff` panel cards, `#f8fafc` canvas ground, `#0f172a` primary slate-navy, `#e2e8f0` precision 1px borders, sharp radii), with zero dark-mode toggle or theme.
- **FR-003**: System MUST provide dynamic role switching across 5 distinct persona workstations: Executive Decision Cockpit, AML Investigator Workstation, Partner Manager Workstation, Compliance & Audit Explorer, and Data Platform Operations Board.
- **FR-004**: System MUST render deterministic Metric Provenance Popovers on hovering or clicking any quantitative figure, displaying Metric ID, Semantic Definition Version, As-Of Timestamp, Origin Engine, Owner Role, and Citation Tag (Principle V).
- **FR-005**: System MUST display an amber `[REPLAY]` badge with timestamp on any narrative, briefing, or chart component served from cached storage during upstream reasoning outages (Principle VIII).
- **FR-006**: System MUST render the Executive Morning Briefing partitioned into 4 distinct horizons: Competitive, Partner, Client, and Financial.
- **FR-007**: System MUST render an interactive 4-domain Causal DAG distinguishing verified causal edges (solid vector, confidence $\ge 0.80$, placebo refuter $p > 0.05$) from unverified correlations (dashed vector) (Principle III).
- **FR-008**: System MUST provide an interactive What-If Shock Slider with sub-200ms parametric propagation updating forward revenue projections and displaying a waterfall attribution chart whose components sum to $100\% \pm 0.01\%$.
- **FR-009**: System MUST display strategic trade-off evaluation cards pairing proposed actions with explicit risk-return projections, trade-offs, and evidentiary citations.
- **FR-010**: System MUST render the AML Investigator triage queue displaying $\le 50$ prioritized high-confidence cases collapsed from raw alerts.
- **FR-011**: System MUST render a one-screen AML evidence dossier collating KYC approval recency, deposit history, round-trip micro-P&L trade velocity, and withdrawal requests.
- **FR-012**: System MUST provide an interactive relational graph canvas rendering connected account clusters while applying hub suppression to CGNAT proxies and public hosting IP addresses ($k > 100$).
- **FR-013**: System MUST provide a near-final Suspicious Activity Report (SAR) narrative editor with 100% metric citation coverage and statutory reference normalization.
- **FR-014**: System MUST display a Partner Churn Radar visualizer ranking partners by Value at Risk $\times P(\text{churn})$ across discrete 30-day intervention windows.
- **FR-015**: System MUST display systemic churn cohort risk maps aggregating partners by geographical region and business segment.
- **FR-016**: System MUST visualize 3-tier sub-affiliate tree hierarchies and detect mirror/opposite trading pairs with timing correlation percentages, size symmetry, and net commission extracted.
- **FR-017**: System MUST provide an immutable Decision Ledger timeline showing sequence numbers (`ledger_seq`), SHA-256 cryptographic chain continuity status, and WORM anchor verification details.
- **FR-018**: System MUST render a two-phase commit Governed Action Shelf anchored at the viewport bottom displaying staged Action Intent Tokens, Cloud KMS ECDSA P-256 signature badges, and execution status (Principle II).
- **FR-019**: System MUST enforce Four-Eyes authorization modals requiring two distinct authenticated officer identity sign-offs prior to committing any High-severity operational action.
- **FR-020**: System MUST render a Data Platform Operations board tracking streaming freshness SLAs ($< 30$s), contract breach dead-letter queue depth, 10-SLO continuous error budget burndown, and Red-Line test gates (RL-1..RL-7).
- **FR-021**: System MUST provide an omnipresent Conversational Copilot Command Bar allowing operators to run natural language queries across the ontology, verified through the Metric Auditor Gate (Feature 007).
- **FR-022**: System MUST provide closed-loop Active Learning Flywheel feedback controls on SAR drafts, alert triage, and partner risk cards, recording operator corrections into the Decision Outcomes Ledger (Feature 014).
- **FR-023**: System MUST render Disaster Recovery Runbook execution proofs, Chaos status indicators, and warm-start cache health metrics on the Data Operations board (Feature 015).
- **FR-024**: System MUST provide a connected full-stack architecture with Next.js App Router API Route Handlers communicating directly with the Python EIOS Cockpit Presentation Services (`eios.cockpit`), with zero contract drift against `specs/012-cockpit/contracts/` JSON Schemas and seamless degradation to cached snapshots with amber `[REPLAY]` badges when offline (Principle VIII).

---

## 4. Success Criteria *(mandatory)*

- **SC-001**: 100% of numerical figures in cockpit views display verifiable metric provenance popovers upon operator hover or click.
- **SC-002**: 100% of narrative cards served during simulated reasoning outages display an amber `[REPLAY]` badge with exact generation timestamp.
- **SC-003**: What-if scenario simulation updates forward projections and 100% additive waterfall attribution charts in $< 200$ ms upon slider adjustment.
- **SC-004**: Zero autonomous write-back capability exists: 100% of operational mutations require explicit human staging and Four-Eyes review in the Governed Action Shelf.
- **SC-005**: Interface strictly complies with Institutional Light Mode standards (`#ffffff` panels, `#f8fafc` canvas ground, slate-navy accents, sharp borders), with 0% dark-mode options.
- **SC-006**: Viewport responsiveness verified across desktop viewports from $1280 \times 800$ to $3840 \times 2160$ with optimal layout density maintained at $1440 \times 900$.
- **SC-007**: 100% of tested user flows across all 5 persona workstations successfully load, display live/cached state, stage governed action tokens, and submit flywheel feedback.
- **SC-008**: Full test suite pass rate of 100% across all frontend component, integration, and contract test suites with zero console errors, hydration mismatches, or contract validation failures.
