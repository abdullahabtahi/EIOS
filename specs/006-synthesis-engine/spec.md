# Feature Specification: Executive Synthesis Engine (F05)

**Feature Branch**: `006-synthesis-engine`  
**Created**: 2026-10-06  
**Status**: Draft  
**Input**: User description: "F05-synthesis-engine: Executive Synthesis Engine delivering cross-domain causal narrative, Structural Causal Model (SCM) DAG with offline/online refutation caching, predictive forecasting beating seasonal-naive baseline (MASE < 1.0) with strictly 100% additive driver attribution, parametric scenario shock simulation, proactive morning briefing generation with replay fallback, and governed recommendation composition with Doubly Robust AIPW propensity score logging per initial_plan.md §5.1, docs/brief/data.md, docs/models_and_evals.md §5, docs/data_products_and_omcp.md, and FEIOS/docs/spikes_and_adrs.md (ADR-005, S-04)."

**Constitution references**:
- **Principle I: LLMs Never Compute Business Metrics** (Every quantitative metric in executive synthesis, forecasts, shock simulations, and morning briefings is retrieved from the Semantic Metric Layer or deterministic causal functions; audited by the Metric Auditor Gate).
- **Principle II: No Autonomous Write-Back** (Recommendations emit proposed Action Intents only, signed with Cloud KMS ECDSA P-256, with zero direct state mutation sinks).
- **Principle III: Honest Uncertainty and the Causal-Evidence Gate** (Causal edges must satisfy: confidence interval excludes zero, placebo-treatment refuter $p > 0.05$ `[TARGET]`, random-common-cause and data-subset stability $\Delta \le 0.20$ `[TARGET]`, confidence $\ge 0.80$ `[TARGET]`; otherwise system outputs mandatory refusal: "correlation detected; insufficient evidence for causation").
- **Principle IV: Data as a Product, Ontology-Only Access** (Synthesis operates over governed Data Products: `competitor_benchmarks`, `partner_360`, `transactions_aml`, `trading_activity`, `platform_operations`, accessed solely via OMCP).
- **Principle V: Provenance and Labelling** (Every figure in briefings, scenario deltas, and forecasts carries `[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, or `[SPIKE]`, and cites entity ID, metric version, and `as_of` timestamp).
- **Principle VI: Eval-First, Baselines and Anti-Circularity** (Forecaster must beat seasonal-naive $y_{t-28}$ on sealed holdouts with $\text{MASE} < 1.0$ `[TARGET]`; driver attribution must beat equal-split baseline and sum strictly to $100.0\% \pm 0.001\%$ `[TARGET]`; placebo edges must be rejected).
- **Principle VII: Specialised Agents and Decoupled Pipelines** (SCMs and refutations are fitted and cached offline/nightly per Spike S-04 / ADR-005 `[SPIKE]`; live conversational turn only performs sub-second parametric shock propagation; no live structural model refitting).
- **Principle VIII: Deterministic Fallback and Operability** (Outages degrade to cached morning briefings and precomputed SCM results marked with `[REPLAY]` badges; p95 query latency within SLAs `[TARGET]`).

---

## Users of the Platform

- **Chief Executive Officer (CEO) / Chief Operating Officer (COO)**: Consumes the daily Morning Briefing, queries high-level cross-domain "why" questions across four business domains (Competitive $\rightarrow$ Partner $\rightarrow$ Client $\rightarrow$ Financial) `[BRIEF data.md]`, and explores counterfactual scenario simulations ("What if competitor X raises payouts by 50 bps?" `[BRIEF data.md]`).
- **Chief Financial Officer (CFO)**: Evaluates 28-day forward revenue and deposit forecasts `[ASSUMPTION]`, reviews 100% additive driver attribution breakdowns `[TARGET]`, and validates margin trade-offs before approving strategic investments.
- **Head of Partnerships / Partner Manager**: Inspects causal linkages between competitor payout aggressions and partner churn hazards, evaluating AI-generated retention playbook recommendations.
- **Forward Deployed Engineer (FDE) / ML Engineer**: Configures the versioned Causal DAG, executes nightly DoWhy/SCM refutation jobs, inspects bootstrap confidence intervals, and monitors AIPW propensity logging for unbiased offline flywheel recalibration.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cross-Domain Causal SCM & Offline/Online Caching Engine (Priority: P1) 🎯 MVP

As an Executive or FDE, I want a versioned Structural Causal Model (SCM) DAG connecting Competitive, Partner, Client, and Financial domains with nightly refutation caching, so that causal linkages are rigorously proven and callable sub-second without risking live pipeline stalls or unverified causal overreach.

**Why this priority**: Implements Constitution Principles III and VII, and satisfies client brief core mandate ("True cross-domain reasoning connecting dots across silos" `[BRIEF data.md]`). Live refutations take tens of seconds (Spike S-04 / ADR-005 `[SPIKE]`); decoupling nightly offline refutation fitting from online sub-second lookup is foundational to all synthesis capabilities.

**Independent Test**: Execute `python -m eios.synthesis.scm_runner --fit-cache`. Assert that the 4-domain causal chain (`competitor_payout_rate` $\rightarrow$ `partner_churn_rate` $\rightarrow$ `ftd_count_28d` $\rightarrow$ `net_deposit_volume_usd` `[ILLUSTRATIVE]`) is fitted on historical data, validated through the Causal-Evidence Gate (placebo refuter $p > 0.05$ `[TARGET]`), cached to disk, and retrievable via OMCP `get_causal_chain` in $< 100\text{ms}$ p95 `[TARGET]`.

**Acceptance Scenarios**:

1. **Given** historical domain data, **When** the nightly SCM refutation engine evaluates the canonical 4-domain DAG, **Then** all edges have non-zero effects, confidence intervals excluding zero, and placebo refutation $p$-values $> 0.05$ `[TARGET]`, writing a signed SCM cache manifest.
2. **Given** a spurious or planted placebo edge (true effect = 0.0 `[TARGET]`), **When** evaluated by the SCM engine, **Then** the placebo refuter rejects the edge ($p \le 0.05$ `[TARGET]`), the edge gate status is set to `FAIL`, and the edge is excluded from causal propagation.
3. **Given** an unrefuted or failed edge query, **When** queried by an agent or user, **Then** the system returns `"correlation detected; insufficient evidence for causation."` per RL-3 `[TARGET]`.
4. **Given** an online query for `get_causal_chain`, **When** invoked, **Then** the system returns the cached edges, weights, confidence intervals, and model version in $< 100\text{ms}$ p95 `[TARGET]` with zero runtime refutation overhead.

---

### User Story 2 - Predictive Forecasting Engine & Additive Driver Attribution (Priority: P1)

As a CFO or Executive, I want forward-looking time-series forecasts with empirical error bounds that beat the seasonal-naive baseline ($\text{MASE} < 1.0$ `[TARGET]`) and decompose variance into root-cause drivers that sum strictly to 100.0% `[TARGET]`, so that I understand exactly why metrics are moving and where to allocate budget.

**Why this priority**: Implements Constitution Principles I and VI, directly fulfilling brief requirement: "Based on current trends, we'll miss revenue target by X%. Root causes: competitive pressure (40%), partner churn (35%), operational issues (25%) [BRIEF data.md]."

**Independent Test**: Run `python -m eios.synthesis.forecast_runner --metric net_deposit_volume_usd --horizon 28`. Assert that candidate forecast beats the seasonal-naive $y_{t-28}$ baseline with $\text{MASE} < 1.0$ `[TARGET]`, produces calibrated $95\%$ prediction intervals `[TARGET]`, and outputs a driver attribution dictionary whose values sum to exactly $100.0\% \pm 0.001\%$ `[TARGET]`.

**Acceptance Scenarios**:

1. **Given** 90 days of synthetic metric history `[ASSUMPTION]`, **When** forecasting a target metric over a 28-day horizon `[ASSUMPTION]`, **Then** the model incorporates leading indicators from upstream DAG nodes and beats the seasonal-naive benchmark with $\text{MASE} < 1.0$ `[TARGET]`.
2. **Given** a forecast variance or target delta, **When** `attribute_drivers()` is invoked, **Then** the system outputs percentage contributions across competitive, partner, operational, and client factors that sum strictly to $100.0\% \pm 0.001\%$ `[TARGET]`.
3. **Given** an eval run on synthetic holdout data with planted ground-truth driver proportions, **When** evaluated against the baseline equal-split ($33.3\% / 33.3\% / 33.3\%$ `[ILLUSTRATIVE]`), **Then** the candidate attribution ranks the top driver with $\ge 90\%$ accuracy `[TARGET]` and achieves significantly lower absolute attribution error.

---

### User Story 3 - Parametric Scenario Shock Simulation Engine (Priority: P2)

As a COO or Executive, I want to inject hypothetical shocks into the causal DAG (e.g., competitor payout changes, platform latency spikes) and simulate downstream impacts with confidence intervals and ranked mitigation actions, so that I can stress-test strategic choices before committing capital.

**Why this priority**: Satisfies client brief mandate: "What happens to our P&L if competitor X acquires competitor Y? What if a competitor raises payouts by 50 bps? [BRIEF data.md]."

**Independent Test**: Execute `python -m eios.synthesis.scenario_runner --shock competitor_payout_rate=0.15`. Assert that downstream impacts on partner churn, first-time deposits, and net deposit volume USD are computed via topological propagation in $< 200\text{ms}$ p95 `[TARGET]` with 95% confidence intervals `[TARGET]` and explicit assumption listings.

**Acceptance Scenarios**:

1. **Given** an exogenous shock specification (e.g. `{"competitor_payout_rate": 0.15}` `[ILLUSTRATIVE]`), **When** `run_scenario` is executed, **Then** the system traverses the cached SCM DAG in topological order and computes propagated deltas and 95% confidence intervals for all reachable downstream metrics in $< 200\text{ms}$ `[TARGET]`.
2. **Given** simulated downstream revenue loss, **When** scenario analysis completes, **Then** the engine ranks pre-configured defensive mitigation actions with estimated ROI ranges and risk trade-offs.
3. **Given** any simulated scenario output, **Then** all underlying modeling assumptions (e.g., linear elasticity bounds, invariance of unshocked covariates) are explicitly emitted alongside the results.

---

### User Story 4 - Proactive Morning Briefing Generator & Streaming Narrative (Priority: P2)

As an Executive (CEO / COO), I want an automated daily Morning Briefing synthesized across all domains that proactively highlights top overnight insights, emerging risks, and identified opportunities with follow-up prompts and replay fallback, so that I start each day informed without digging through dashboards.

**Why this priority**: Directly fulfills client brief "Blow our minds" requirement: "Good morning. Here's what changed overnight: 3 insights requiring attention, 2 emerging risks, 1 opportunity identified. Shall I elaborate on any? [BRIEF data.md]."

**Independent Test**: Execute `python -m eios.synthesis.briefing_runner --date 2026-10-06`. Assert generation of a structured `BriefingObject` containing ranked insights, risks, opportunities, follow-up drill-downs, and verified tool citations, validating against the Metric Auditor Gate in $< 3\text{s}$ p95 `[TARGET]`.

**Acceptance Scenarios**:

1. **Given** overnight metric arrivals across all domains, **When** the scheduled Morning Briefing job executes, **Then** it generates a structured briefing object containing $\ge 3$ ranked insights `[BRIEF]`, $\ge 2$ emerging risks `[BRIEF]`, $\ge 1$ high-upside opportunity `[BRIEF]`, and interactive follow-up prompt suggestions.
2. **Given** briefing narrative text, **When** scanned by the Metric Auditor Gate, **Then** 100% of numerical business assertions match tool outputs from the Semantic Metric Layer with valid entity IDs and timestamps (0 hallucinations `[TARGET]`).
3. **Given** an upstream LLM outage or gateway timeout, **When** a user requests the morning briefing, **Then** the system serves the last cached briefing with a prominent `[REPLAY]` badge and timestamp.

---

### User Story 5 - Governed Recommendation Composer & Doubly Robust AIPW Propensity Logging (Priority: P3)

As an FDE and Compliance Officer, I want action recommendations composed with complete impact bounds, multi-factor trade-offs, and logged propensity scores $e(X)$, so that human officers can evaluate options safely and the offline decision flywheel can recalibrate causal edge weights without confounding-by-indication.

**Why this priority**: Implements Constitution Principles II and VI, and `initial_plan.md` §5.1 / §6.1. Without logging the agent's proposal propensity score $e(X)$ at recommendation time, historical human acceptance creates severe selection bias ("confounding-by-indication"), corrupting offline causal retraining.

**Independent Test**: Compose an action recommendation via `python -m eios.synthesis.recommendation_runner`. Assert that the resulting draft Action Intent contains estimated impact range, pros/cons trade-offs, confidence score ($\ge 0.80$ `[TARGET]`), evidence citations, and logged propensity score $e(X) \in [0.01, 0.99]$ `[ASSUMPTION]` alongside causal context vector $X$.

**Acceptance Scenarios**:

1. **Given** a detected risk or opportunity, **When** the recommendation composer executes, **Then** it outputs structured decision cards with: impact estimate range, multi-factor trade-offs (pros/cons), confidence level ($\ge 0.80$ `[TARGET]`), evidence citations, and linked Action Type.
2. **Given** an action intent proposal, **When** formatted for the Action Intent Hub, **Then** the proposing agent calculates and records the propensity score $e(X) = P(\text{Action Proposed} \mid X)$ and causal covariate vector $X$.
3. **Given** logged decision outcomes in the decision ledger, **When** the Doubly Robust AIPW recalibration routine runs, **Then** treatment uplift is estimated using inverse propensity weighting, proving recovery of true planted treatment effects with $\ge 50\%$ lower bias than naive averages `[TARGET]`.

---

### User Story 6 - Canonical OMCP Synthesis Tools & Router Integration (Priority: P3)

As an AI Agent or Cockpit UI client, I want canonical OMCP tool handlers (`get_causal_chain`, `run_scenario`, `get_forecast`, `get_briefing`, `propose_action`) exposed through `OMCPServer`, so that conversational agents and dashboards access synthesis capabilities through a uniform, governed interface.

**Why this priority**: Implements Constitution Principle IV (Ontology-Only Access). All capabilities must be consumable via standardized OMCP tool contracts (`contracts/omcp-tools.json`).

**Independent Test**: Run `python -m pytest tests/synthesis/test_omcp_synthesis_tools.py`. Assert that `OMCPServer` dispatches all 5 synthesis tools cleanly, enforces security markings, and passes the Metric Auditor Gate with zero untraceable numbers `[TARGET]`.

**Acceptance Scenarios**:

1. **Given** valid tool inputs to `OMCPServer`, **When** calling `get_causal_chain`, `run_scenario`, `get_forecast`, or `get_briefing`, **Then** responses conform strictly to tool schema contracts and return deterministic, audit-ready data in $< 100\text{ms}$ `[TARGET]`.
2. **Given** an agent generating a conversational answer from synthesis tool results, **When** audited by `audit(response, tool_outputs)`, **Then** the auditor confirms `ok = true` with 0 untraceable numbers and 0 uncited claims `[TARGET]`.

---

## Edge Cases & Defensive Architecture

- **Causal Graph Directed Cycle**: If a user-configured or learned edge introduces a directed cycle in the SCM, the engine MUST reject the DAG with `CausalCycleError` during validation (SCM must be a strict DAG).
- **Multicollinearity & Degenerate Matrices**: If historical predictor variables have near-zero variance or high collinearity during structural equation fitting, Ridge regularization ($L_2$ penalty $\alpha = 1.0$ `[ASSUMPTION]`) MUST prevent singular matrix inversion or numerical explosion.
- **Unreachable Metrics in Shock Propagation**: If a shocked metric has no directed causal path to a requested downstream metric in the DAG, the engine MUST return a delta of $0.0$, a confidence interval of $[0.0, 0.0]$, and an informational trace indicating no directed causal dependency.
- **Zero Variance in Driver Attribution**: If all upstream driver path impacts are exactly zero ($\sum |I_j| = 0.0$), the attribution engine MUST fall back to a balanced uniform allocation ($100 / K \%$ each) to strictly preserve the $100.0\% \pm 0.001\%$ invariant `[TARGET]`.
- **Extreme Scenario Extrapolation**: If an exogenous shock exceeds historical domain bounds (e.g. $> 3\sigma$ or $+500\%$ payout rate), the scenario engine MUST flag an `ExtrapolationWarning` and widen confidence intervals non-linearly using quadratic residual scaling.
- **Extreme Propensity Truncation**: Propensity scores $e(X)$ near 0 or 1 create explosive inverse propensity weights $\frac{1}{e(X)}$. The engine MUST strictly clip propensity scores to the bounded interval $[0.01, 0.99]$ `[ASSUMPTION]`.
- **Auditor Gate Circuit Breaker**: If LLM narrative generation generates an untraceable business metric failing `MetricAuditorGate`, the system MUST abort text output and serve a deterministic formatted template populated directly from verified tool results with zero ungrounded tokens.
- **Provider Outage During Briefing**: If upstream model providers time out, the briefing service MUST serve the latest verified cached briefing tagged with `is_cached_replay: true` and a visible `[REPLAY]` badge.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST represent the cross-domain causal network as a versioned directed acyclic graph (SCM DAG) spanning Competitive, Partner, Client, and Financial domains.
- **FR-002**: System MUST implement offline structural equation fitting and DoWhy-style refutation tests (placebo-treatment refuter, random common cause, data subset) per Spike S-04 / ADR-005 `[SPIKE]`.
- **FR-003**: System MUST enforce the Causal-Evidence Gate: an edge is approved for causal propagation ONLY IF its effect 95% CI excludes zero `[TARGET]`, placebo refuter $p > 0.05$ `[TARGET]`, refuter stability $\Delta \le 0.20$ `[TARGET]`, and confidence $\ge 0.80$ `[TARGET]`.
- **FR-004**: System MUST serialize verified SCM DAGs, edge weights, and refutation manifests into a versioned cache (`SCMCache`) for sub-second online retrieval.
- **FR-005**: System MUST output `"correlation detected; insufficient evidence for causation."` whenever an unverified, unrefuted, or failed edge is queried.
- **FR-006**: System MUST expose `get_causal_chain(outcome_metric, window_days)` via OMCP, returning edges, effect weights, confidence intervals, gate verdicts, and model version in $< 100\text{ms}$ p95 `[TARGET]`.
- **FR-007**: System MUST provide a time-series forecasting engine incorporating leading indicators from upstream SCM nodes to forecast target metrics over a configurable horizon (7 to 28 days `[ASSUMPTION]`).
- **FR-008**: System MUST beat the seasonal-naive $y_{t-28}$ baseline on synthetic holdout sets with $\text{MASE} < 1.0$ `[TARGET]` and calibrated 95% prediction intervals.
- **FR-009**: System MUST decompose forecast misses or metric variances into additive driver attributions across candidate drivers that strictly sum to $100.0\% \pm 0.001\%$ `[TARGET]`.
- **FR-010**: System MUST expose `get_forecast(metric_id, horizon)` via OMCP, returning point estimates, prediction intervals, and 100% additive driver attributions.
- **FR-011**: System MUST achieve superior driver attribution ranking accuracy over the equal-split baseline ($33.3\% / 33.3\% / 33.3\%$ `[ILLUSTRATIVE]`) when evaluated on ground-truth synthetic data.
- **FR-012**: System MUST implement parametric shock injection (`run_scenario(shock_spec)`) traversing the SCM DAG in topological order.
- **FR-013**: System MUST compute propagated deltas and 95% confidence intervals for all reachable downstream metrics in $< 200\text{ms}$ p95 `[TARGET]`.
- **FR-014**: System MUST evaluate and rank defensive mitigation actions (with estimated ROI ranges and risk trade-offs) for adverse simulated scenario outcomes.
- **FR-015**: System MUST explicitly enumerate modeling assumptions alongside scenario propagation outputs.
- **FR-016**: System MUST expose `run_scenario(shock_spec)` via OMCP.
- **FR-017**: System MUST generate a structured daily Morning Briefing object (`BriefingObject`) categorizing $\ge 3$ insights `[BRIEF]`, $\ge 2$ risks `[BRIEF]`, and $\ge 1$ opportunity `[BRIEF]` with executive summaries and drill-down prompts.
- **FR-018**: System MUST verify that 100% of numerical figures in briefing narratives trace directly to Semantic Metric Layer tool results via the Metric Auditor Gate (0 untraceable numbers `[TARGET]`).
- **FR-019**: System MUST provide deterministic cached replay with `[REPLAY]` metadata in the event of LLM gateway failure or timeout.
- **FR-020**: System MUST expose `get_briefing(date)` via OMCP.
- **FR-021**: System MUST compose structured recommendation cards containing: impact range, multi-factor trade-offs (pros/cons), confidence level ($\ge 0.80$ `[TARGET]`), evidence citations, and linked Action Types.
- **FR-022**: System MUST calculate and record propensity scores $e(X) = P(\text{Action Proposed} \mid X) \in [0.01, 0.99]$ `[ASSUMPTION]` and causal context vectors $X$ on every proposed Action Intent Token.
- **FR-023**: System MUST implement an Augmented Inverse Propensity Weighting (AIPW) estimator for offline decision ledger recalibration, recovering true treatment effects on synthetic data.
- **FR-024**: System MUST integrate proposed action intents with the `ActionIntentHub` using KMS-signed draft tokens with zero direct mutation.
- **FR-025**: System MUST wire all 5 synthesis handlers (`get_causal_chain`, `run_scenario`, `get_forecast`, `get_briefing`, `propose_action`) into `OMCPServer`.
- **FR-026**: System MUST enforce server-side security markings and tenant isolation across all synthesis tool outputs.
- **FR-027**: System MUST pass 100% of Red-Line CI gates (RL-1 through RL-7) with zero tolerance `[TARGET]`.
- **FR-028**: System MUST achieve $\ge 80\%$ line and branch test coverage across all synthesis modules `[TARGET]`.

---

## Success Criteria *(mandatory)*

- **SC-001 (Causal Gate Accuracy & Latency)**: 100% of valid DAG edges pass refutation; 100% of planted placebo edges are rejected ($p \le 0.05$ `[TARGET]`); online `get_causal_chain` latency p95 is $< 100\text{ms}$ `[TARGET]`.
- **SC-002 (Forecast Precision)**: Forecast model achieves $\text{MASE} < 1.0$ `[TARGET]` against seasonal-naive $y_{t-28}$ on synthetic holdout sets with 95% interval coverage within nominal $\pm 5\%$ `[TARGET]`.
- **SC-003 (Attribution Exactness)**: Driver attribution decomposes variance into constituent factors summing to exactly $100.0\% \pm 0.001\%$ `[TARGET]`, and correctly identifies the primary ground-truth driver with $\ge 90\%$ accuracy `[TARGET]`.
- **SC-004 (Scenario Simulation Latency & Bounds)**: Parametric scenario propagation executes in $< 200\text{ms}$ p95 `[TARGET]` with directional sign accuracy $\ge 95\%$ compared to synthetic ground-truth intervention response `[TARGET]`.
- **SC-005 (Briefing Synthesis & Audit Pass Rate)**: Morning briefing generates $\ge 3$ insights `[BRIEF]`, $\ge 2$ risks `[BRIEF]`, and $\ge 1$ opportunity `[BRIEF]`, passing the Metric Auditor Gate with 0 hallucinated metrics and 100% citation coverage `[TARGET]`.
- **SC-006 (AIPW Flywheel Bias Reduction)**: AIPW offline estimator achieves $\ge 50\%$ lower bias than naive observational averages on synthetic decision outcome logs with confounded selection `[TARGET]`.
- **SC-007 (Test Coverage & Code Health)**: Full unit and integration test suite passes with $\ge 80\%$ statement and branch coverage `[TARGET]`, with clean `ruff check` and `ruff format` execution (0 errors `[TARGET]`).

---

## Key Domain Entities

- `CausalDAG`: Directed acyclic graph representation of cross-domain metrics with directional edges, structural weights, and confidence intervals.
- `SCMRefutationReport`: Refutation test results (placebo treatment $p$-value, random common cause stability, data subset stability) certifying causal validity.
- `SCMCache`: Serialized, versioned cache of certified causal edges, structural weights, and refutation manifests.
- `ForecastResult`: Time-series forecast containing point estimates, lower/upper 95% bounds, historical MASE score, and additive driver attribution dictionary summing strictly to 100.0%.
- `ScenarioShockSpec`: Exogenous shock input specifying target metric, delta percentage/value, and optional duration.
- `ScenarioSimulationResult`: Propagated downstream metric impacts with confidence intervals, underlying assumptions, and ranked defensive action recommendations.
- `BriefingObject`: Daily executive briefing containing ranked insights, emerging risks, identified opportunities, and follow-up drill-down suggestions.
- `RecommendationCard`: Structured decision proposal with impact quantification, multi-factor pros/cons, confidence, evidence citations, and linked Action Type.
- `AIPWPropensityRecord`: Propensity score $e(X)$, causal covariate context $X$, proposed action type, and logged downstream outcome for offline flywheel recalibration.
