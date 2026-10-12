# Feature Specification: Production-Grade Partner Churn & Retention Intelligence Hardening

**Feature Branch**: `020-production-partner-intelligence`  
**Created**: 2026-10-12  
**Status**: Ready for Planning  
**Input**: Comprehensive elevation from static hackathon prototype to Tier-1 Enterprise Production Grade (Palantir Foundry Workshop + QuantumBlack Horizons + Google Cloud Engineering Rigor) addressing the 6 critical blind spots identified in the Partner Manager Workstation: portfolio-scale dual scatter-grid triage, 30d/90d historical decay trajectories, live backend DoWhy causal refutation, driver-adaptive playbooks, 1-click cohort batch remediation, and closed-loop outcome calibration.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Synchronized Dual Scatter-Triage Grid & Portfolio Scale (Priority: P1)

As a Senior Partner Manager managing over 200 high-value affiliate partners, I need a synchronized master-detail interface featuring both the 2D Cartesian Churn Hazard Radar and a high-density, sortable portfolio triage grid so that I can rapidly search, filter, and prioritize partners by Value at Risk, Churn Probability, and Intervention Urgency without being limited to a static handful of plotted points.

- **Why this priority**: Solves the "5 mock dots" scale illusion. In production, relationship managers cannot triage a real portfolio without search, sort, and table-scatter synchronization.
- **Independent Test**: Load the Partner Workstation; search for "LatAm" or sort the table by VaR descending; clicking a table row highlights the corresponding node on the radar with projected crosshairs, and selecting a quadrant on the radar filters the table.
- **Acceptance Scenarios**:
  1. **Given** a portfolio of 50+ partners, **When** the operator types a query in the triage search box (e.g., "PTR-882" or "Colombia"), **Then** both the table and scatter plot filter in real time ($< 50\text{ms}$).
  2. **Given** the scatter radar, **When** the operator clicks the "CRITICAL (3)" segmented filter, **Then** the triage table updates synchronously to display only partners with $P(\text{churn}) \ge 0.50$.
  3. **Given** a partner row in the triage grid, **When** the operator clicks the row, **Then** the canvas centers crosshairs on that node and the Copilot Dossier displays that partner's 360 telemetry.

---

### User Story 2 - 30D/90D Historical Decay Trajectories & Change-Point Breadcrumbs (Priority: P1)

As an Institutional Partner Manager and Risk Analyst, I need to visualize the temporal drift path of at-risk partners over the past 30 to 90 days with velocity sparklines so that I can immediately distinguish acute sudden disengagement (e.g., rival poaching) from slow secular decline or temporary seasonal dips.

- **Why this priority**: Churn is a continuous survival process, not a point-in-time snapshot. Operators must understand *where the partner came from* before deciding whether to intervene.
- **Independent Test**: Select partner `PTR-882`; the radar renders dotted historical trajectory breadcrumbs showing its drift path from $T-30\text{d}$ ($P=0.22$) through $T-14\text{d}$ ($P=0.55$) to $T-0\text{d}$ ($P=0.78$), accompanied by a 30-day velocity sparkline.
- **Acceptance Scenarios**:
  1. **Given** an at-risk partner node, **When** the operator hovers or selects the node, **Then** the radar draws a historical trajectory path with directional chevrons indicating the velocity and direction of risk migration across quadrants.
  2. **Given** the Diagnostic Inspector, **When** viewing the selected partner, **Then** a 30-day sparkline renders daily login frequency and turnover velocity alongside the PELT change-point detection timestamp.
  3. **Given** a partner experiencing a documented seasonal holiday dip, **When** the hazard model runs, **Then** the seasonal suppression rule caps hazard at $\le 0.15$, preventing false alarms.

---

### User Story 3 - Live Backend Causal SCM Refutation & What-If Concession API (Priority: P2)

As a Relationship Director authorized to deploy commercial concessions, I need the interactive Counterfactual Retention Simulator to query the live backend DoWhy SCM causal inference endpoint (`POST /api/v1/churn/partner/{id}/what-if`) so that I receive mathematically validated retention lift estimates, Placebo treatment test $p$-values, and Gemini 3.8 Flash causal explanations rather than client-side linear approximations.

- **Why this priority**: Fulfills Constitution Principle I & III (LLMs never compute metrics; causal claims must pass statistical refutation). Prevents deceptive client-side simulation facades.
- **Independent Test**: Drag the VIP Concession slider to 70% and release (`onPointerUp`); verify a network POST request to `/api/v1/churn/partner/{id}/what-if` returns with `causal_refuter_p_value >= 0.40`, projected net margin lift, and Gemini 3.8 Flash causal rationale.
- **Acceptance Scenarios**:
  1. **Given** the What-If slider in the Radar Studio, **When** the operator adjusts the concession intensity, **Then** the component dispatches an API request and displays the backend-returned retention lift percentage and 95% confidence interval ($+74\% \pm 8\%$).
  2. **Given** a proposed concession that dilutes net broker spread margin by $>35\%$, **When** the backend evaluates the proposal, **Then** the response flags `MARGIN_DILUTIVE_WARNING` and recommends a pareto-optimal compromise.
  3. **Given** the live simulated coordinate, **When** the backend responds, **Then** the simulated emerald node on the radar updates to reflect the true causal estimate.

---

### User Story 4 - Driver-Adaptive Action Playbooks & 1-Click Cohort Batch Remediation (Priority: P2)

As an Operations Desk Lead, I need the Governed Action Shelf to offer specific, pre-configured retention playbooks tailored to the identified root cause (Cashier Latency, Competitor Poaching, Rebate Dispute) and allow 1-click batch remediation when viewing systemic regional cohorts so that I can resolve multi-partner bottlenecks in a single governed motion.

- **Why this priority**: Eliminates the "one-size-fits-all" button flaw and enables rapid systemic remediation across entire geographic partner clusters.
- **Independent Test**: In individual view, verify action buttons change depending on whether the primary driver is "Operational Cashier" or "Competitive Poaching". In Cohort view, click "Batch Stage LatAm Cashier Whitelist"; verify 3 distinct partner action intents are staged with Cloud KMS P-256 nonces.
- **Acceptance Scenarios**:
  1. **Given** partner `PTR-882` with primary driver "Cashier Latency", **When** viewing the action launcher, **Then** the primary action is `Whitelist Direct VIP Cashier Rail` (\$0 P&L cost, LatAm Treasury Desk).
  2. **Given** partner `PTR-419` with primary driver "Competitor Poaching", **When** viewing the action launcher, **Then** the primary action is `Deploy Spread Rebate Match (+1.20/lot)` (Commercial Desk).
  3. **Given** the `COHORTS` view highlighting the LatAm cohort, **When** the operator clicks `Batch Stage LatAm Cashier Rail Whitelist`, **Then** the system stages a multi-target Two-Phase Commit proposal protecting all 3 partners (\$837K Total VaR).

---

### User Story 5 - Closed-Loop Experience Library & Active Learning Calibration (Priority: P3)

As a System Auditor and Head of Partner Operations, I need the Partner Workstation to display the empirical outcome success rates from past retention playbooks (Experience Library) and the live Brier calibration score ($< 0.10$) of the shadow hazard model so that operators and executive leadership have verified proof that the system learns from historical interventions.

- **Why this priority**: Fulfills Constitution Principle VI (Eval-first, active learning flywheel, and outcome tracking). Proves the AI system gets smarter over time.
- **Independent Test**: Open the Diagnostics panel in the Radar Studio; verify it displays the historical playbook success rate (e.g., 78.5% retention across 14 historical deals) and the real-time shadow model Brier score ($0.082$).
- **Acceptance Scenarios**:
  1. **Given** any recommended playbook, **When** the operator inspects its card, **Then** the UI shows historical empirical evidence: `Historical Win Rate: 78.5% (11/14 retained over 180d)`.
  2. **Given** the Active Learning Flywheel telemetry, **When** new trade outcomes are processed, **Then** the Brier calibration score and Population Stability Index (PSI) update dynamically.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a high-density, sortable Triage Grid component synchronized bi-directionally with the 2D Cartesian Churn Radar canvas.
- **FR-002**: Triage Grid MUST support sorting by Partner ID, Tier, 30D VaR, $P(\text{churn})$, and Days to Churn, and filtering via text query in $< 50\text{ms}$.
- **FR-003**: Churn Radar Canvas MUST render 30-day historical drift trajectories showing the migration path of at-risk partners ($T-30\text{d}$, $T-14\text{d}$, $T-0\text{d}$) with directional chevrons.
- **FR-004**: System MUST connect the Counterfactual Retention Simulator slider to the backend `POST /api/v1/churn/partner/{partner_id}/what-if` endpoint with automatic request debouncing ($250\text{ms}$).
- **FR-005**: Backend What-If endpoint MUST return DoWhy SCM causal refuter verification metrics ($p$-value, confidence intervals, and margin impact).
- **FR-006**: System MUST dynamically adapt recommended action buttons in the inspector based on the partner's primary diagnosed driver (`Operational/Cashier`, `Competitive Poaching`, `Commercial Rebate`).
- **FR-007**: System MUST support 1-click batch action staging for regional cohorts in `COHORTS` mode, generating atomic action proposals for all cohort members.
- **FR-008**: System MUST display historical playbook win-rate ratios from the Experience Library and live shadow model Brier calibration scores ($< 0.10$).
- **FR-009**: All UI views (embedded and full-screen studio) MUST strictly adhere to Institutional Sovereign Light Mode (`#FFFFFF`, `#F8FAFC`, `#0F172A`) with WCAG AAA contrast halos.
- **FR-010**: All staged actions MUST require Cloud KMS P-256 asymmetric signatures and Two-Phase Commit governance before execution.

---

## Success Criteria *(mandatory)*

- **SC-001**: Operator triage throughput increases from 4 partners/hour to $\ge 20\text{ partners/hour}$ using the synchronized dual scatter-grid interface.
- **SC-002**: Zero client-side mathematical hallucinations: 100% of causal lift estimates, confidence bounds, and $p$-values trace directly to backend SCM endpoints (Constitution Principle I & III).
- **SC-003**: 100% test pass rate across all unit, component, and API test suites with zero TypeScript compiler errors.
- **SC-004**: Sub-50ms client-side filter and sorting latency across 50+ monitored partner profiles.
- **SC-005**: 1-click cohort batch remediation successfully stages actions across all cohort partners in $< 200\text{ms}$.
