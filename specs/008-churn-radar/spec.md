# Feature Specification: Partner Churn Radar (Module C / Slice S2)

**Feature Branch**: `008-churn-radar`  
**Created**: 2026-10-07  
**Status**: Ready for Implementation (v3 Super-Spec)  
**Standard**: QuantumBlack (McKinsey *Rewired*) Horizon Architecture × Palantir Foundry Kinetic Ontology × Google Cloud Reference Architecture  
**Primary Brief Ground Truth**: `docs/brief/churn` `[BRIEF churn]`  
**Companion Architectural Docs**: `initial_plan.md` §5.2, `docs/models_and_evals.md` §4, `docs/data_products_and_omcp.md` §2-§4  

---

## 1. Executive Framing & Business Problem

In enterprise affiliate and introducing broker (IB) networks, partner churn is invisible until it is irreversible `[BRIEF churn]`. By the time relationship managers observe collapsed trading volumes or overt partner migration to competitors, months of customer acquisition revenue have been lost and the commercial relationship is dead `[BRIEF churn]`. 

Relationship managers currently operate reactively: they manage hundreds of accounts manually and only intervene when partners submit angry support tickets or when monthly commission payments plummet `[BRIEF churn]`. Crucially:
1. **Silent Disengagement**: High-performing partners slowly reduce activity, decay login frequency, and redirect traffic weeks before complete abandonment `[BRIEF churn]`.
2. **Value Asymmetry**: A small percentage of top-tier partners generate the majority of retail customer referrals `[BRIEF churn]`. Losing a Tier-1 partner creates massive P&L exposure.
3. **Alert Fatigue (The False Alarm Trap)**: Generic monitoring rules trigger massive false alarms on seasonal trading dips, weekend market pauses, and regional holidays, degrading operational trust `[BRIEF churn]`.

**The Solution**: An AI-powered **Partner Churn Radar** delivering:
- A **Discrete-Time Hazard Model** over five multi-modal signal families to compute a calibrated 30-day disengagement probability $P(\text{churn})$.
- **Seasonality-Aware Change-Point Detection** that robustly filters temporary volatility from true structural disengagement.
- **Value-at-Risk Prioritization** (`Priority Score = P(churn) × Value-at-Risk`) rendering a unified operational queue for Partner Managers.
- **Explainable AI & GenAI Pattern Discovery** synthesizing deterministic root causes and uncovering novel unstructured disengagement themes across support tickets.
- **Governed Action Playbooks (The Causal Flywheel)** staging KMS-signed `ActionIntentToken` proposals for human sign-off, closing the operational learning loop via Doubly Robust Augmented Inverse Propensity Weighting (AIPW).

---

## 2. Labelling & Traceability Convention

Every figure, metric, and scenario in this specification strictly adheres to `initial_plan.md` §0.2:
- `[BRIEF churn]`: Direct requirement from `docs/brief/churn`.
- `[TARGET]`: Formal quantitative commitment to be measured in CI/eval harness.
- `[ASSUMPTION]`: Operational or engineering parameter chosen for this engagement.
- `[ILLUSTRATIVE]`: Synthesized demo personas and seeded generator examples.

---

## 3. Operational Workflows & User Scenarios *(mandatory)*

### User Story 1 - Value-at-Risk Operational Prioritization (Priority: P1) `[BRIEF churn]`

As a **Partner Relationship Manager**, I want a single operational queue of partners ranked by `Value-at-Risk × Churn Probability`, so that I can focus my daily retention interventions on high-value partners before disengagement becomes irreversible.

- **Why this priority**: Focuses limited relationship manager bandwidth on maximum revenue preservation rather than sorting through unweighted risk scores.
- **Independent Test**: Query OMCP tool `get_partner_signals` across the partner universe; verify the resulting Workshop queue orders partners monotonically by `priority_score = hazard_probability_30d * value_at_risk_usd`.
- **Acceptance Scenarios**:
  1. **Given** 1,000 active partners in DuckDB hot state, **When** the Partner Manager opens the Churn Radar Workshop, **Then** accounts are rendered in descending order of `priority_score` with high/medium/low tier designations.
  2. **Given** Partner `P-CHURN-DRIFT` (Tier 1, $45,000/mo commission `[ILLUSTRATIVE]`) with a 0.72 hazard score, and Partner `P-MICRO-99` (Tier 3, $200/mo commission `[ILLUSTRATIVE]`) with a 0.95 hazard score, **When** the priority queue is generated, **Then** `P-CHURN-DRIFT` is ranked significantly higher in operational urgency due to $32,400 Value-at-Risk.

---

### User Story 2 - Explainable Risk Tiers & Root-Cause Attribution (Priority: P1) `[BRIEF churn]`

As a **Partner Relationship Manager**, I want transparent, plain-language explanations citing specific signal drivers (e.g., "38% login decay WoW", "Competitor commission mentioned in support ticket"), so that I understand *why* the partner is at risk and have immediate context to tailor my outreach.

- **Why this priority**: In McKinsey/Palantir methodology, operational adoption collapses without explainability. Managers will not call a VIP partner based on an opaque black-box probability.
- **Independent Test**: Retrieve a High-Risk partner profile via OMCP; verify that the output contains a deterministic feature contribution breakdown across the 5 signal families and an audited natural-language narrative.
- **Acceptance Scenarios**:
  1. **Given** Partner `P-CHURN-DRIFT` flagged as High Risk, **When** inspecting their entity card, **Then** the UI displays the top contributing signal families with direct L1 data citations (e.g., `partner_engagement_signals` login velocity -42%, `partner_comms` ticket #8492 mentioning "competitor revshare").
  2. **Given** model explanations rendered in prose, **When** scanned by the Metric Auditor Gate, **Then** 100% of numerical assertions trace to deterministic tool outputs with 0 metric hallucinations `[TARGET]`.

---

### User Story 3 - Seasonality-Aware Anomaly Filtering (Zero False Alarms) (Priority: P1) `[BRIEF churn]`

As a **Partner Relationship Manager**, I want the system to distinguish between temporary seasonal dips (e.g., weekend market pauses, summer holidays, Ramadan) and genuine structural disengagement, so that I am never disturbed by false alarms.

- **Why this priority**: The brief states: *"Minimise false positives — alert fatigue damages manager effectiveness."* `[BRIEF churn]`
- **Independent Test**: Inject a synthetic 14-day holiday pause into Partner `P-HARD-NEG-VACATION` with zero logins and zero clicks; verify the change-point detector classifies this as a seasonal dip and does NOT emit a High-Risk disengagement alert.
- **Acceptance Scenarios**:
  1. **Given** Partner `P-HARD-NEG-VACATION` who takes a 2-week vacation during a known seasonal window with zero platform activity, **When** the change-point algorithm runs, **Then** the rolling baseline filter suppresses the alert, keeping risk status at `LOW`.
  2. **Given** Partner `P-CHURN-DRIFT` exhibiting a sustained 3-week decline on active trading days (Mon-Fri) with negative support tickets, **When** processed, **Then** the change-point algorithm confirms structural drift and flags the anomaly.

---

### User Story 4 - Systemic Regional & Cohort Risk Detection (Priority: P2) `[BRIEF churn]`

As the **Head of Partnerships**, I want to receive real-time cohort-level alerts when multiple partners in a region or segment exhibit synchronized disengagement, so that I can execute systemic commercial counter-measures rather than isolated account calls.

- **Why this priority**: Uncovers aggressive competitor poaching campaigns (e.g., rival broker offering 65% revshare in Southeast Asia) before regional market share collapses.
- **Independent Test**: Query OMCP function `get_high_risk_cohorts`; verify that a synthetic cluster of 15 partners in Southeast Asia (`IDN_MYS`) triggers a cohort anomaly alert with aggregated Value-at-Risk.
- **Acceptance Scenarios**:
  1. **Given** 15 partners in region `IDN_MYS` showing synchronized FTD drops following a competitor marketing campaign, **When** the cohort detector runs, **Then** it surfaces a single systemic alert: `"Warning: 15 partners in SEA showing synchronized disengagement; competitor promotion suspected"` `[BRIEF churn]`.

---

### User Story 5 - Governed Retention Playbooks & The Closed-Loop Flywheel (Priority: P2) `[BRIEF churn]`

As a **Partner Manager / Data Scientist**, I want the system to recommend governed retention playbooks (`LaunchRetentionPlaybook`) as non-autonomous `ActionIntentToken` proposals, and log observed outcomes to the `Decision_Ledger` so that the model continuously learns which interventions actually work.

- **Why this priority**: Completes the Palantir Kinetic Ontology loop (Insight → Action → Learning Flywheel).
- **Independent Test**: Propose an action via OMCP `propose_action`; verify an ECDSA P-256 signed `ActionIntentToken` is emitted in `PENDING` state with an attached propensity score $e(X)$; verify simulated execution writes to `Decision_Ledger` for Doubly Robust AIPW recalibration.
- **Acceptance Scenarios**:
  1. **Given** a high-risk partner driven by financial/commission dissatisfaction, **When** the system generates recommendations, **Then** it proposes `LaunchRetentionPlaybook` with playbook `Offer_Tier_Upgrade` and stages it for human sign-off.
  2. **Given** 100 historical retention actions recorded in `Decision_Ledger`, **When** the offline learning job runs, **Then** it calculates the Average Treatment Effect (ATE) using Doubly Robust AIPW and recalibrates playbook selection weights.

---

### User Story 6 - GenAI Emerging Pattern Discovery (Priority: P2) `[BRIEF churn]`

As a **Data Scientist / Head of Partnerships**, I want an autonomous GenAI agent to analyze unstructured support communications across churning cohorts to discover novel, previously unindexed churn patterns without manual hypothesis formulation.

- **Why this priority**: Directly fulfills the hackathon "Blow Our Minds" bar: *"Pattern discovery: New churn pattern detected: partners with unresolved technical issues for extended periods have significantly higher churn rates"* `[BRIEF churn]`.
- **Independent Test**: Execute the `PatternDiscoverySpecialist` over a synthetic corpus of support tickets; verify it clusters unresolved issues and articulates a structured, novel churn hypothesis.
- **Acceptance Scenarios**:
  1. **Given** 25 churned partners who logged support tickets regarding MT5 WebSocket latency spikes, **When** the GenAI pattern discovery agent runs, **Then** it generates a structured insight card identifying "Unresolved MT5 WebSocket latency" as an emerging churn driver with supporting evidence citations.

---

## 4. Ground-Truth Golden Test Personas *(mandatory for live demo)*

To guarantee flawless live demo execution and deterministic evaluation, the system seeds three canonical partner personas in the synthetic data foundry:

| Persona ID | Name / Role | Baseline Trajectory | Planted Anomaly | Expected Model Output |
| :--- | :--- | :--- | :--- | :--- |
| `P-CHURN-DRIFT` | **VIP Master IB (Southeast Asia)** | $45,000/mo commission; 80 active clients; 18 months tenure `[ILLUSTRATIVE]` | 40% WoW login decay over 3 weeks; support ticket #8492: *"Competitor is offering 60% revshare and zero spread markups"* `[BRIEF churn]` | **Tier**: HIGH (`hazard = 0.76`, `priority_score = $34,200`). **Explanation**: Login decay + competitor poaching terms cited. Recommends VIP retention playbook. |
| `P-HARD-NEG-VACATION` | **Tier-2 European Affiliate** | $8,500/mo commission; 25 active clients; 24 months tenure `[ILLUSTRATIVE]` | Zero logins and zero clicks for 14 consecutive days during August holiday; zero negative support tickets | **Tier**: LOW (`hazard = 0.12`). **Change-point**: Classifies drop as temporary seasonal pause. Alert suppressed. (Zero false alarm). |
| `P-COHORT-SEA-CLUSTER` | **Regional Cluster (15 Affiliates)** | Combined $180,000/mo commission across Indonesia & Malaysia `[ILLUSTRATIVE]` | Synchronized 30% drop in FTDs over 10 days coinciding with rival broker's zero-swap promotion | **Cohort Alert**: Systemic risk detected in SEA. Aggregated Value-at-Risk surfaced in cockpit with regional playbook recommendation. |

---

## 5. Functional & Architectural Requirements

### 5.1 Logic Layer: Discrete-Time Hazard & Change-Point Model
- **FR-001 (Operational Churn Definition)**: The ground-truth event $T$ (Churn) is formally defined as: **Zero active referred clients (0 trades) AND $\ge 80\%$ drop in trailing 30-day commission volume compared to the partner's 60-day historical baseline** `[TARGET]`.
- **FR-002 (Discrete-Time Hazard Parameterization)**: The system MUST formulate survival probability across four weekly person-period intervals $t \in \{1, 2, 3, 4\}$ using a logistic hazard model:
  $$\text{logit}(h_{it}) = \alpha_t + \boldsymbol{\beta}^T \mathbf{X}_{it}$$
  where $\alpha_t$ is the baseline hazard and $\mathbf{X}_{it}$ spans the five signal families `[TARGET]`.
- **FR-003 (Five Signal Families)**: The model feature vector $\mathbf{X}$ MUST compute features strictly from the canonical L1 Data Products:
  1. *Behavioral*: Login velocity, referral volume decay, click-to-FTD conversion trend (`partner_engagement_signals`).
  2. *Communication*: Unresolved ticket ratio, ticket sentiment, manager outreach response latency (`partner_comms`).
  3. *Relationship / Network*: Partner tier, tenure months, sub-affiliate tree activity (`partner_360`, `partner_referral_tree`).
  4. *Financial*: 30-day commission delta, payment dispute flags (`commission_ledger`, `financial_pnl`).
  5. *Competitive*: Competitor spread differentials, competitor poaching keywords in tickets (`competitor_benchmarks`, `partner_comms`).
- **FR-004 (Seasonality-Aware Change-Point Detection)**: The system MUST compute Week-over-Week (WoW) engagement ratios normalized by market trading days (excluding weekends and public holidays). An anomaly is flagged ONLY if:
  $$\text{WoW\_Ratio} < \text{Median}(\text{WoW}) - 3.0 \times \text{MAD}(\text{WoW})$$
  sustained across $\ge 2$ consecutive active trading weeks `[TARGET]`.
- **FR-005 (Intervention Window Timing)**: The system MUST identify the *optimal intervention window*, defined as the period where $0.35 \le P(\text{churn}) \le 0.75$. Partners with $P(\text{churn}) > 0.85$ MUST be flagged as "Late-Stage Disengagement" where low-cost retention has $<10\%$ historical efficacy.

### 5.2 Ontology Layer: Palantir Kinetic Ontology Mapping
- **FR-006 (Kinetic Object Hydration)**: The system MUST extend the canonical `Partner` ontology object ([objects.py](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/src/eios/ontology/core/objects.py)) with live properties: `hazard_probability_30d`, `priority_score`, `risk_tier`, `intervention_window`, and `churn_explanation`.
- **FR-007 (Zero-Latency Read Access)**: All computed scores MUST be written into DuckDB hot state (`partner_360` / `churn_radar_scores` table), guaranteeing sub-5ms OMCP read access for Workshop applications `[TARGET]`.

### 5.3 Action & Governance Layer: Four-Eyes State Machine & Causal Flywheel
- **FR-008 (KMS-Signed Action Intent)**: When proposing a retention intervention, the system MUST emit a governed `ActionIntentToken` matching [intent_hub.py](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/FEIOS/src/eios/ontology/actions/intent_hub.py), specifying `action_type="LaunchRetentionPlaybook"`, cryptographic ECDSA P-256 signature, 15-minute expiry nonce, and the estimated propensity score $e(X)$ `[TARGET]`.
- **FR-009 (Simulated Write-Back & Ledger)**: Executed actions MUST write back to the simulated sink and be recorded in the append-only `Decision_Ledger` with an atomic sequence number (`ledger_seq`) and cryptographic SHA-256 hash chaining `[TARGET]`.
- **FR-010 (Doubly Robust AIPW Recalibration)**: The closed-loop flywheel MUST compute Average Treatment Effect (ATE) using Augmented Inverse Propensity Weighting (AIPW) over 60-day forward outcomes to eliminate confounding by indication before updating playbook weights `[TARGET]`.

### 5.4 GenAI & Conversational Analytics Layer
- **FR-011 (GenAI Pattern Discovery)**: The `PatternDiscoverySpecialist` MUST run asynchronously over unstructured ticket text, extracting sentiment, competitor mentions, and clustering novel disengagement themes via Vertex AI Gemini 1.5 with strict Pydantic egress schema `[TARGET]`.
- **FR-012 (Metric Auditor Egress Gate)**: All conversational answers generated by `ChurnRadarSpecialist` MUST be verified by the Metric Auditor Gate; any response containing unverified metrics or ungrounded statistics MUST be rejected `[TARGET]`.
- **FR-013 (Deterministic Replay Fallback)**: If LLM APIs or external gateways fail, the system MUST immediately serve cached golden explanation templates marked with `[REPLAY]` badges (Principle VIII) `[TARGET]`.

---

## 6. Success Criteria & Target Metrics *(mandatory)*

| Metric ID | Dimension | Evaluation Method | Baseline | Target Commitment `[TARGET]` |
| :--- | :--- | :--- | :--- | :--- |
| **SC-001** | **Predictive Discrimination** | PR-AUC on 30-day sealed holdout dataset | Naive "no login > 14 days" rule | **PR-AUC $\ge$ Baseline + 0.10** (minimum 0.78 absolute) |
| **SC-002** | **Early Warning Lead Time** | Median days between first alert and actual churn event | Naive "no login > 14 days" rule | **Lead Time $\ge$ Baseline + 7 Days** (median $\ge 18$ days advance warning) |
| **SC-003** | **False Positive Suppression** | False Positive Rate on seeded seasonal holiday dips | Static 30% volume drop rule | **FPR $\le 5\%$** on `P-HARD-NEG-VACATION` class |
| **SC-004** | **Cohort Risk Recovery** | Recall on planted regional competitor poaching clusters | Per-partner independent alerts | **100% recall** on planted 15-partner SEA cluster (`P-COHORT-SEA-CLUSTER`) |
| **SC-005** | **Metric Auditor Compliance** | Hallucination scan on 100 generated explanation narratives | Human review | **0 untraceable business metrics** (100% citation coverage) |
| **SC-006** | **Decision Latency** | P95 latency for OMCP `get_partner_signals` query | Cloud Run SLA | **P95 $< 50\text{ms}$** from DuckDB hot state |
| **SC-007** | **Live Demo Readiness** | End-to-end execution of `quickstart.md` golden scenarios | Automated test script | **100% pass** across all 3 golden test personas in $< 15\text{s}$ |

---

## 7. Assumptions & Technical Constraints

- `[ASSUMPTION]`: Prediction horizon is fixed at 30 days for operational responsiveness, with secondary 60-day monitoring for outcomes.
- `[ASSUMPTION]`: Partners with tenure $< 14$ days are assigned to an "Onboarding Watchlist" rather than the discrete hazard model due to sparse history.
- `[ASSUMPTION]`: The simulated write-back sink provides immediate execution confirmation for demo and eval runs.
- `[CONSTRAINT]`: Constitution Principle I: Zero LLM math. All hazard probabilities and priority scores are calculated in deterministic Python (`lifelines` / `numpy` / `pandas`).
- `[CONSTRAINT]`: Constitution Principle II: Zero autonomous write-back. All mutations require signed `ActionIntentToken` records.
