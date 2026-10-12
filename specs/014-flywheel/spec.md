# Feature Specification: Closed-Loop Decision Learning Flywheel & Counterfactual Causal Recalibration (014-flywheel)

**Feature Branch**: `014-flywheel`  
**Created**: 2026-10-09  
**Status**: Ready for Planning  
**Input**: Closed-Loop Decision Learning Flywheel & Counterfactual Causal Recalibration (`014-flywheel` / F13 / Slice S5)  
**Authoritative References**: `initial_plan.md` §3.1 (L5), §6.1, §12; `docs/engagement_plan.md` §2, §5 (Risk R12); `docs/models_and_evals.md`; `.specify/memory/constitution.md` (Principles I, II, III, V, VI, VII)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Horizon Decision Outcomes Ledger & Reconciliation (Priority: P1) 🎯 MVP

As an Executive Risk Officer or Operations Lead, I need an immutable, append-only Decision Outcomes Ledger that tracks every proposed and approved action intent alongside the agent's baseline propensity score and reconciles forward actual performance against predictions at 30-day, 60-day, and 90-day intervals, so that the organization maintains rigorous accountability and empirical auditability over all automated recommendations.

**Why this priority**: Without tracking what was proposed, why it was proposed, and what actually occurred across standardized horizons, closed-loop learning is impossible and organizational trust degrades.

**Independent Test**: Propose an intervention action; simulate execution; ingest forward outcome observations at 30d, 60d, and 90d milestones; verify that prediction residuals and attribution linkages are stored with tamper-evident provenance.

**Acceptance Scenarios**:
1. **Given** an action intent token proposed by an autonomous agent, **When** the intent is approved and executed, **Then** the system records the decision along with its proposal-time propensity score, baseline contextual covariates, and forecast horizon milestones (30d, 60d, 90d).
2. **Given** an active entry in the outcomes ledger, **When** milestone outcome data arrives, **Then** the system reconciles predicted financial impact, retention rates, or risk mitigation against actual realized values and calculates forecast residuals.

---

### User Story 2 - Doubly Robust AIPW Causal Uplift Estimator (Priority: P1)

As a Lead Quantitative Researcher or Causal Inference Engineer, I need an unbiased causal uplift estimator using Augmented Inverse Propensity Weighting (AIPW) that corrects for confounding by indication (the operational reality that human operators selectively approve interventions on higher-risk accounts), so that the platform determines true counterfactual treatment effects rather than misleading observational correlations.

**Why this priority**: In high-stakes enterprise environments, naive averages falsely suggest interventions harm accounts because officers only intervene on severe cases. Doubly Robust AIPW guarantees unbiased estimates even if either the propensity score model or the outcome regression model is imperfectly specified.

**Independent Test**: Provide an observational dataset with synthetic confounding by indication (e.g., treatment assigned with 85% probability to high-risk cases); compute Average Treatment Effect (ATE) using AIPW; verify that estimated uplift recovers ground-truth treatment effect within nominal confidence bounds while naive difference-in-means fails.

**Acceptance Scenarios**:
1. **Given** historical decision outcomes with non-random operator approval patterns, **When** the causal estimation pipeline executes, **Then** the system computes Doubly Robust AIPW uplift estimates with standard errors and 95% confidence intervals.
2. **Given** an estimated causal treatment effect, **When** evaluated against the Causal-Evidence Gate, **Then** the effect must exclude zero, pass random common cause and placebo treatment refutations, and satisfy stability thresholds before being marked certified for model recalibration.

---

### User Story 3 - Automated SCM DAG Edge-Weight Recalibration (Priority: P2)

As a Strategic Planner or Enterprise Architect, I need the platform to periodically and offline recalibrate Structural Causal Model (SCM) Directed Acyclic Graph (DAG) edge coefficients based on realized decision prediction residuals, so that scenario simulations and what-if propagations continuously reflect real-world dynamics without requiring manual code adjustments.

**Why this priority**: Fixed causal model weights drift over time as market dynamics, fraud syndicates, and partner behaviors shift. Autonomous offline recalibration ensures scenario forecasting remains accurate.

**Independent Test**: Inject a dataset with a known shift in elasticity between partner commission and retention; run offline DAG recalibration; verify that updated edge coefficients reflect the empirical shift and produce versioned checkpoint artifacts without breaking DAG acyclicity.

**Acceptance Scenarios**:
1. **Given** accumulated 30/60/90-day outcome residuals exceeding calibration thresholds, **When** the offline recalibration process runs, **Then** edge coefficients in the causal DAG are updated via regularized counterfactual weighting.
2. **Given** updated edge weights, **When** validating model integrity, **Then** the system verifies acyclicity, stability bounds, and saves an immutable, versioned DAG checkpoint tagged with evaluation metrics.

---

### User Story 4 - Decision Policy Confidence & Playbook Prior Recalibration (Priority: P2)

As a Frontline Operator (AML Investigator, Partner Relationship Manager, or Executive), I need recommendation rankings, expected payoff distributions, and decision confidence popovers to reflect empirical win-rates from the decision ledger, so that I can make faster, higher-conviction decisions backed by proven track records.

**Why this priority**: When human operators see that recommendations update dynamically based on historical realized successes and failures, operator adoption and compliance increase significantly.

**Independent Test**: Simulate an intervention policy that historically yields higher-than-expected recovery; execute policy recalibration; verify that future recommendations for similar accounts display higher confidence ratings and updated empirical success probability bands.

**Acceptance Scenarios**:
1. **Given** empirical outcome data for specific intervention typologies (e.g., proactive partner fee restructuring), **When** policy priors are recalibrated, **Then** future recommendation cards display updated empirical win-rates and narrowed confidence intervals.
2. **Given** an intervention with declining historical efficacy, **When** evaluated, **Then** the system downgrades its ranking, flags elevated uncertainty, and suggests alternative actions.

---

### User Story 5 - Model Calibration Diagnostics & Operations Workstation Integration (Priority: P3)

As a Data Platform Operator or MLOps Engineer, I need real-time visibility into Expected Calibration Error (ECE), Brier scores, reliability diagrams, and concept drift indicators on the Operations Workstation, so that I can detect model degradation before operational performance suffers.

**Why this priority**: Transparent diagnostics allow engineering and risk teams to monitor model health, anticipate drift, and intervene if real-world conditions diverge from model assumptions.

**Independent Test**: Query system calibration status via canonical operational tools; verify export of Brier scores, ECE percentiles, and drift warning flags for all active models.

**Acceptance Scenarios**:
1. **Given** predictions and realized outcomes across all operational modules, **When** querying model calibration health, **Then** the platform returns Expected Calibration Error (ECE), Brier scores, and bin-level reliability curves.
2. **Given** a model whose ECE exceeds operational thresholds (> 0.15), **When** calibration diagnostics run, **Then** the system raises a calibration drift warning and marks the corresponding policy as requiring review.

---

## Edge Cases

- **Extreme Propensity Scores ($e(X) \to 0$ or $e(X) \to 1$)**: When an action is almost always or almost never proposed for certain profiles, inverse propensity weights can explode. The system MUST apply robust clipping (Winsorization) bounds ($[0.01, 0.99]$) to prevent high-variance instability.
- **Sparse Sample Size ($N < 30$ Outcomes)**: In rare intervention categories with minimal historical data, the system MUST NOT fit complex high-dimensional regression models or force recalibration; it MUST fall back to conservative priors and flag "insufficient empirical sample size for automated recalibration."
- **Incomplete Milestone Reporting**: An action may have reached the 30-day milestone while 60-day and 90-day milestones remain pending. The system MUST evaluate partial horizons without corrupting multi-stage temporal alignment.
- **Unobserved Confounding / Sudden Regime Shifts**: Macroeconomic shocks or regulatory revisions may violate the unconfoundedness assumption. Causal refuter checks MUST detect instability and reject causal attribution.
- **Conflicting Treatment Uplift across Cohorts**: If an intervention demonstrates positive uplift on Enterprise accounts but negative uplift on Micro accounts, aggregate pooling can obscure harm. The system MUST support cohort-stratified conditional average treatment effect (CATE) reporting.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST record every approved and executed action intent in an append-only `DecisionOutcomesLedger` with unique identifier, timestamp, and proposing agent identity.
- **FR-002**: System MUST capture and store the proposing agent's propensity score $e(X)$ and pre-treatment contextual covariates at the exact moment of proposal.
- **FR-003**: System MUST record forward outcome milestones at 30-day, 60-day, and 90-day evaluation horizons.
- **FR-004**: System MUST calculate forecast residuals by comparing pre-intervention predicted impact against realized post-intervention outcomes across all evaluation horizons.
- **FR-005**: System MUST implement Doubly Robust Augmented Inverse Propensity Weighting (AIPW) to estimate Average Treatment Effects (ATE) without confounding-by-indication bias.
- **FR-006**: System MUST enforce propensity score clipping to $[0.01, 0.99]$ to guarantee numerical stability under extreme selection probabilities.
- **FR-007**: System MUST compute 95% confidence intervals and standard errors for all causal effect estimates using analytical influence functions or bootstrap resampling.
- **FR-008**: System MUST subject all proposed causal uplift values to the Causal-Evidence Gate (Principle III), requiring effect confidence intervals to exclude zero and passing placebo refuter checks.
- **FR-009**: System MUST support offline batch execution of the recalibration flywheel (Principle VII) to ensure interactive turn coordinators remain decoupled and deterministic.
- **FR-010**: System MUST recalculate Structural Causal Model (SCM) DAG edge weights using empirical outcome residuals and generate versioned DAG artifacts.
- **FR-011**: System MUST guarantee that recalibrated DAG edge weights preserve directed acyclic graph topology without introducing cycles or invalid causal paths.
- **FR-012**: System MUST recalibrate action playbook confidence priors, updating empirical success probability bands and expected payoff estimates.
- **FR-013**: System MUST compute Expected Calibration Error (ECE) and Brier scores across all decision policies.
- **FR-014**: System MUST trigger an operational calibration drift alert if a model's ECE exceeds $0.15$ or if prediction residuals exceed configured tolerance bands.
- **FR-015**: System MUST compute and report Conditional Average Treatment Effects (CATE) across partner and account tier cohorts to expose heterogeneous treatment impacts.
- **FR-016**: System MUST provide deterministic replay and historical backtesting capabilities over historical ledger milestones.
- **FR-017**: System MUST record all recalibrated parameters and DAG versions into the immutable decision audit trail with cryptographic SHA-256 hash digests.
- **FR-018**: System MUST expose decision flywheel metrics and calibration summaries via canonical OMCP tools to the Operations Workstation.
- **FR-019**: System MUST enforce Constitution Principle I: all statistical metrics, Brier scores, AIPW estimators, and residuals MUST be computed deterministically, never hallucinated by language models.
- **FR-020**: System MUST gracefully handle sparse data scenarios ($N < 30$), preserving conservative baseline priors and marking policies with explicit confidence labels.

---

### Key Entities

- **DecisionOutcomeRecord**: Represents an individual action decision, tracking proposal covariates, agent propensity score, executed intervention, and multi-horizon realized outcomes (30d, 60d, 90d).
- **CausalUpliftEstimate**: Contains estimated Average Treatment Effect (ATE), standard error, 95% confidence bounds, propensity overlap statistics, and Causal-Evidence Gate verification status.
- **SCMRecalibrationCheckpoint**: An immutable, versioned snapshot of the Structural Causal Model DAG containing recalibrated edge weights, timestamp, evaluation seed, and residual fit metrics.
- **CalibrationDiagnosticsReport**: Summarizes model reliability, Expected Calibration Error (ECE), Brier scores, reliability diagram bin distributions, and drift indicators.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Decision reconciliation across 1,000 multi-horizon ledger records executes in under 2 seconds.
- **SC-002**: Doubly Robust AIPW estimator reduces treatment effect estimation bias by at least 80% compared to naive observational averages on confounded synthetic benchmark data.
- **SC-003**: 100% of causal assertions and recalibration triggers pass the Causal-Evidence Gate (95% CI excludes zero, placebo effect $\approx 0$).
- **SC-004**: Offline DAG edge-weight recalibration runs end-to-end and produces validated checkpoints in under 5 seconds.
- **SC-005**: All calibrated decision policies achieve an Expected Calibration Error (ECE) under 0.10 on holdout validation data.
- **SC-006**: 100% of quantitative figures, residuals, and calibration scores trace directly to deterministic calculations (zero unverified claims / Principle I compliance).
- **SC-007**: Frontline recommendation confidence ratings reflect empirical outcome accuracy within a 10% tolerance band.
- **SC-008**: Operations Workstation retrieves complete system calibration and drift status in under 200 milliseconds.

---

## Assumptions

- Pre-treatment covariates $X$ and agent propensity score $e(X)$ are logged at proposal time by the action intent infrastructure.
- In synthetic evaluation modes, 30-day, 60-day, and 90-day outcomes are generated via forward-simulation from reproducible seed holdouts rather than waiting real calendar time (`docs/synthetic_data_strategy.md`).
- Offline batch flywheel executions occur periodically (e.g., nightly or on scheduled triggers) without blocking interactive agent turns.
- Unobserved confounding is assumed minimal when conditioning on rich pre-treatment behavioral and financial features, verified by refuter checks.
