# Implementation Plan: Partner Churn Radar (Module C / Slice S2)

**Branch**: `008-churn-radar` | **Date**: 2026-10-07 | **Spec**: [specs/008-churn-radar/spec.md](spec.md)

**Input**: Feature specification from `specs/008-churn-radar/spec.md`, `initial_plan.md` §5.2, `docs/brief/churn` `[BRIEF churn]`, `docs/models_and_evals.md` §4, and `FEIOS/docs/spikes_and_adrs.md` (ADR-003, ADR-016, ADR-017).

---

## 1. Summary

Deliver **Module C: Partner Churn Radar** (completing Slice S2), operationalizing predictive disengagement intelligence and proactive retention workflows for the Deriv Enterprise Intelligence Operating System. The architecture implements a **Discrete-Time Hazard Model** (via `lifelines` and `pandas`) across five multi-modal signal families to compute calibrated 30-day disengagement risk, coupled with **Seasonality-Aware Change-Point Detection** (CUSUM with Day-of-Week and market-calendar normalization) to eliminate weekend/holiday false alarms `[TARGET FPR <= 5%]`. 

It computes a **Value-at-Risk Priority Queue** (`Priority = P(churn) * Value-at-Risk`) for relationship managers, detects **Systemic Regional Cohort Anomalies**, stages non-autonomous **Retention Playbook Action Intents** (KMS-signed ECDSA P-256 tokens) to close the learning loop via **Doubly Robust AIPW Recalibration**, and deploys an autonomous **Pattern Discovery Specialist** powered by Vertex AI (Gemini 1.5) with strict Pydantic schema validation and deterministic replay fallback.

---

## 2. Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: 
- `lifelines>=0.29.0` (Discrete-time hazard regression, Kaplan-Meier, Cox PH)
- `pandas>=2.2.0`, `numpy>=1.26.0`, `scipy>=1.13.0` (Feature engineering, rolling MAD, CUSUM)
- `duckdb>=1.1.0` (Semantic metric layer & hot state store)
- `pydantic>=2.13.5` (Strict domain contracts, action schemas, LLM structured egress)
- `cryptography>=42.0.0` (ECDSA P-256 KMS mock signatures)
- `langgraph>=0.2.0` (Specialist agent integration with Conversation Engine)
- `langchain-google-vertexai>=2.0.0` (Pattern discovery extraction with structured schema)

**Storage**: 
- In-process DuckDB Hot State (`HotStateEngine`) hosting `partner_360`, `churn_radar_scores`, and `churn_cohort_alerts`
- Append-only `Decision_Ledger` simulated sink with atomic `ledger_seq` counter and SHA-256 hash chaining

**Testing**: 
- `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`
- Sealed holdout evaluation against naive "no login > 14 days" baseline (`tests/churn/test_hazard_eval.py`)

**Target Platform**: Linux Server / macOS / Google Cloud Run worker  
**Performance Goals**:
- Batch Hazard Model Training & Inference: $< 30\text{s}$ for 10,000 synthetic partners `[TARGET]`
- Online OMCP `get_partner_signals` Query Latency: $< 50\text{ms}$ p95 from DuckDB hot state `[TARGET]`
- GenAI Pattern Discovery Interactive Latency: $< 3.5\text{s}$ p95 with structured output caching `[TARGET]`
- Batch AIPW Flywheel Recalibration: $< 10\text{s}$ for 5,000 logged decisions `[TARGET]`

**Constraints**:
- Constitution Principle I: Zero LLM metric math (Hazard and Priority calculations strictly in deterministic Python) `[TARGET]`
- Constitution Principle II: Zero autonomous write-back (KMS-signed `ActionIntentToken` proposals only) `[TARGET]`
- Constitution Principle IV: All analytical data consumed strictly via OMCP tools and canonical L1 Data Products
- Constitution Principle VII: Decoupled pipelines; offline hazard compute completely independent of conversational turn execution
- Constitution Principle VIII: Deterministic cached replay fallback with `[REPLAY]` badges for all LLM calls

---

## 3. Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (LLMs Never Compute Metrics)**: PASS. All hazard probabilities, change points, priority scores, and cohort statistics are calculated by deterministic Python modules (`lifelines`, `scipy`, `pandas`). GenAI is restricted to extracting qualitative themes from support tickets and synthesizing plain-language explanations of deterministic features.
- **Principle II (No Autonomous Write-Back)**: PASS. Interventions are proposed as KMS-signed `ActionIntentToken` objects with `status=ActionStatus.PENDING`. No direct update or insert into production operational systems exists in code.
- **Principle III (Honest Uncertainty & Causal Gate)**: PASS. Playbook recommendations cite historical uplift intervals; unobserved cohorts emit "insufficient intervention history" warnings.
- **Principle IV (Ontology-Only Access)**: PASS. All signals derive from canonical L1 Data Products (`partner_360`, `partner_referral_tree`, `commission_ledger`, `partner_engagement_signals`, `partner_comms`, `financial_pnl`, `competitor_benchmarks`) via OMCP.
- **Principle V (Provenance & Labelling)**: PASS. Every churn explanation explicitly cites contributing signal IDs and timestamps. Numbers carry `[TARGET]`, `[ASSUMPTION]`, or `[ILLUSTRATIVE]` tags.
- **Principle VI (Eval-First & Baselines)**: PASS. The hazard model must beat the pre-registered "no login > 14 days" baseline by $\ge 0.10$ PR-AUC on sealed holdout seeds (`test_hazard_model_beats_baseline`).
- **Principle VII (Decoupled Pipelines & Specialized Agents)**: PASS. Offline batch scoring runs independently of real-time query serving. Conversational queries are routed through `ChurnRadarSpecialist`.
- **Principle VIII (Deterministic Fallback)**: PASS. If Vertex AI is unreachable or rate-limited, the system falls back to cached golden explanation templates marked with `[REPLAY]` badges.

---

## 4. Architecture & Component Topology

```text
FEIOS/
├── src/eios/
│   ├── churn/                          # Dedicated Churn Radar Engine (Slice S2)
│   │   ├── __init__.py                 # Public package exports
│   │   ├── models.py                   # Pydantic v2 schemas: ChurnFeatureVector, HazardScore, CohortAlert
│   │   ├── hazard_model.py             # Lifelines Discrete-Time Logistic Hazard Estimator & Inference
│   │   ├── change_point.py             # Seasonality-aware CUSUM & rolling MAD anomaly detector
│   │   ├── cohort_detector.py          # Regional & segment permutation/Z-test systemic risk aggregator
│   │   ├── pattern_discovery.py        # Vertex AI GenAI agent for unstructured ticket theme clustering
│   │   ├── flywheel.py                 # Doubly Robust AIPW causal estimator for playbook recalibration
│   │   └── pipeline.py                 # Batch coordinator: L1 Data Products -> Features -> DuckDB Hot State
│   ├── conversation/
│   │   └── specialists/
│   │       └── churn.py                # ChurnRadarSpecialist: OMCP-grounded multi-turn conversational agent
│   └── ontology/
│       ├── core/
│       │   └── objects.py              # Extended Partner entity with dynamic churn properties
│       ├── functions/
│       │   └── partner.py              # Upgraded partner_value_at_risk and churn_priority functions
│       └── omcp/
│           └── server.py               # Canonical OMCP tool handlers: get_partner_signals, get_high_risk_cohorts
```

---

## 5. Project Structure & Deliverables

### Documentation (this feature)
```text
specs/008-churn-radar/
├── spec.md                             # Feature specification (McKinsey/Palantir v3 Super-Spec)
├── plan.md                             # This implementation plan
├── research.md                         # Mathematical formulations, ADRs & technology choices
├── data-model.md                       # Pydantic v2 domain models, OMCP entities & DuckDB DDL
├── quickstart.md                       # Golden persona walkthrough & verification scripts
├── contracts/
│   ├── omcp_actions.md                 # OMCP tool schemas & ActionIntent specifications
│   ├── partner-signals-response.schema.json
│   └── cohort-alerts-response.schema.json
└── checklists/
    └── requirements.md                 # Spec quality checklist
```

### Source Code & Test Layout
```text
FEIOS/
├── src/eios/churn/                     # Implementation modules (hazard, change point, cohort, flywheel, GenAI)
├── scripts/
│   ├── run_churn_pipeline.py           # CLI tool to run end-to-end batch scoring
│   ├── test_churn_pattern_discovery.py # Interactive GenAI pattern extraction demo
│   └── test_retention_intent.py        # Action intent creation and signature verification demo
└── tests/
    └── churn/                          # Comprehensive evaluation test suite
        ├── conftest.py                 # Seeded synthetic fixtures (P-CHURN-DRIFT, P-HARD-NEG, P-COHORT)
        ├── test_hazard_model.py        # Unit tests for person-period transformation and hazard math
        ├── test_change_point.py        # Anomaly detector tests verifying suppression of seasonal dips
        ├── test_cohort_detector.py     # Systemic cluster detection tests on planted SEA cluster
        ├── test_pattern_discovery.py   # GenAI extraction tests with mock and live Vertex AI
        ├── test_flywheel_aipw.py       # Doubly Robust AIPW recovery of planted intervention uplift
        ├── test_omcp_churn_tools.py    # OMCP tool handler integration tests (sub-50ms SLA)
        └── test_churn_radar_eval.py    # Blocking eval harness: beats baseline by >= 0.10 PR-AUC
```

---

## 6. Complexity Tracking

> **Constitution Check has zero violations. No unjustified complexity introduced.**

| Component | Justification | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| **Discrete-Time Logistic Hazard Model** | Accommodates right-censored data, time-varying covariates across 4 weekly intervals, and yields true hazard probabilities. | Standard binary classification (e.g. static XGBoost) ignores censoring, treats 1-day churn identically to 29-day churn, and suffers severe lookahead bias. |
| **Market-Calendar CUSUM Anomaly Filter** | Required to prevent weekend and regional holiday false alarm storms `[BRIEF churn]`. | Naive rolling Z-score / MAD flags 38% of active partners every weekend when FX markets close. |
| **Doubly Robust AIPW Flywheel** | Relationship managers selectively intervene on distressed VIP accounts (confounding by indication). AIPW eliminates selection bias. | Naive observed conversion comparisons exhibit Simpson's Paradox, falsely indicating that retention playbooks cause churn. |
| **Asynchronous GenAI Pattern Discovery** | Isolates LLM context size and latency ($<3.5\text{s}$) from deterministic online API serving ($<50\text{ms}$). | Running LLM inference synchronously during partner score queries breaches latency SLOs and risks hallucination. |
