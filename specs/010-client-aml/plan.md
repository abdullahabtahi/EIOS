# Implementation Plan: Client Fraud Sentinel / AML Transaction Monitoring (Module A / Slice S4)

**Branch**: `010-client-aml` | **Date**: 2026-10-07 | **Spec**: [specs/010-client-aml/spec.md](spec.md)

**Input**: Feature specification from `specs/010-client-aml/spec.md`, `initial_plan.md` §5.4, `docs/brief/monitoring.md` `[BRIEF monitoring]`, `docs/models_and_evals.md` §2, `.specify/memory/constitution.md`.

---

## 1. Summary

Deliver **Module A: Client Fraud Sentinel / AML Transaction Monitoring** (completing Slice S4), operationalizing real-time and batch financial crime surveillance across retail client transactions for the Deriv Enterprise Intelligence Operating System. The architecture tackles the core operational challenge of alert fatigue by deploying a **Supervised Alert Triage Scorer** that filters ~2,000 weekly rule alerts down to $\le 50$ high-confidence investigation cases `[BRIEF monitoring]` retaining $\ge 90\%$ of true laundering events `[TARGET]`.

It implements **Dual-Horizon Behavioral Baselines** (peer cohort baselines for cold start transitioning to personalized robust Z-scores for mature accounts), a deterministic **Round-Trip Sequence Detector** catching "$500 deposit $\to$ 10 min trading with $0.01 profit $\to$ withdraw within 72h of KYC approval" typologies `[BRIEF monitoring]`, and a **Degree-Penalized Bipartite Graph Clustering Engine** that isolates coordinated mule rings while suppressing public Wi-Fi and CGNAT hubs. A **Real-Time Pre-Withdrawal Sentinel** assesses transactions in $< 2.0\text{s}$ (p95) `[TARGET]` and emits Cloud KMS ECDSA P-256 signed `HoldWithdrawal` proposals (never auto-executing, per Principle II). An automated **SAR Composer** drafts regulator-ready filings with 100% cited metrics and normalized statutory citations (`31 CFR 1010`), passing the Metric Auditor Gate and providing deterministic replay fallback under LLM outage.

---

## 2. Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**:
- `scipy>=1.13.0`, `numpy>=1.26.0`, `pandas>=2.2.0` (Robust MAD dispersion, exponential weighting, sequence matching)
- `networkx>=3.2.0` (Bipartite graph clustering, degree-penalized hub suppression, Adamic-Adar edge weighting)
- `duckdb>=1.1.0` (In-process columnar hot-state analytical engine)
- `pydantic>=2.13.5` (Strict domain schemas and JSON Schema contract validation)
- `cryptography>=42.0.0` (ECDSA P-256 KMS mock signatures and verification)
- `langgraph>=0.2.0` (Supervisory Router and Blackboard architecture integration)

**Storage**:
- In-process DuckDB Hot State (`HotStateEngine`) hosting `aml_alert_scores`, `aml_roundtrip_events`, `aml_mule_rings`, `aml_withdrawal_assessments`, and `aml_case_dossiers`
- Append-only `Decision_Ledger` simulated sink with atomic `ledger_seq` counter and SHA-256 hash chaining

**Testing**:
- `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`
- Sealed holdout evaluation comparing alert triage scorer against pre-registered naive rule baseline (`tests/aml/test_aml_eval.py`)

**Target Platform**: Linux Server / macOS / Google Cloud Run worker  
**Performance Goals**:
- Alert Queue Triage: $< 200\text{ms}$ for 2,000 alerts `[TARGET]`
- Real-Time Pre-Withdrawal Risk Evaluation: $< 2.0\text{s}$ (p95) `[TARGET]`
- Network Mule Ring Graph Clustering: $< 300\text{ms}$ per network cluster query `[TARGET]`
- Automated Dossier & SAR Compilation: $< 2.5\text{s}$ across 5+ source systems `[TARGET]`
- Memory Footprint: Bounded in-memory hot state with sliding-window pruning ($< 500\text{MB}$) `[TARGET]`

**Constraints**:
- **Constitution Principle I**: Zero LLM metric math (all risk scores, exposure dollars, and p-values calculated deterministically) `[TARGET]`
- **Constitution Principle II**: Zero autonomous write-back (all fund holds and freezes require KMS-signed proposals and authenticated human sign-off) `[TARGET]`
- **Constitution Principle IV**: All analytical data consumed strictly via OMCP tools and canonical L1 Data Products; PII strictly pseudonymized via `tok_id_cluster_<hex16>`
- **Constitution Principle VI**: Alert triage scorer must beat pre-registered naive rule baseline by $\ge 0.15$ PR-AUC on sealed seeds
- **Constitution Principle VII**: Statutory citations (`31 CFR 1010`, `31 U.S.C. 5318(g)`) normalized to prevent false Auditor Gate rejections
- **Constitution Principle VIII**: Deterministic replay fallback with `[REPLAY]` badges for all conversational and SAR summaries

---

## 3. Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (LLMs Never Compute Metrics)**: PASS. All triage probabilities, Z-scores, net trading P&Ls, market exposure percentages, and graph centrality figures are calculated by deterministic Python modules (`scipy`, `numpy`, `networkx`). LLMs are strictly confined to narrative phrasing and evidence citation.
- **Principle II (No Autonomous Write-Back)**: PASS. Pre-withdrawal interventions emit KMS-signed `ActionIntentToken` objects (`HoldWithdrawal`, `FreezeAccount`) placed in `PENDING` status. Human sign-off is mandatory before execution against the simulated sink.
- **Principle III (Honest Uncertainty & Causal Gate)**: PASS. Statistical deviations cite confidence intervals and p-values ($p < 0.001$). Ambiguous patterns emit "insufficient behavioral evidence" warnings.
- **Principle IV (Ontology-Only Access)**: PASS. All inputs derive from canonical L1 Data Products (`transactions_aml`, `trading_activity`, `device_network_graph`, `compliance_cases`). Raw PII is never exposed; entity clusters use `tok_id_cluster_<hex16>`.
- **Principle V (Provenance & Labelling)**: PASS. All claims cite specific transaction IDs and timestamps. Numbers carry `[TARGET]`, `[ASSUMPTION]`, or `[BRIEF monitoring]` provenance tags.
- **Principle VI (Eval-First & Baselines)**: PASS. A naive threshold rule baseline ("deposit $> \$10,000$ or velocity $> 3$") is implemented first and must be beaten by $\ge 0.15$ PR-AUC on sealed holdout seeds.
- **Principle VII (Decoupled Pipelines & Specialized Agents)**: PASS. Batch alert scoring runs independently of real-time withdrawal checks. Conversational queries route through `SentinelAMLSpecialist`.
- **Principle VIII (Deterministic Fallback)**: PASS. If external LLM calls fail, SAR narratives and dossier briefings degrade to deterministic golden template fallbacks with `[REPLAY]` badges.

---

## 4. Architecture & Component Topology

```text
FEIOS/
├── src/eios/
│   ├── aml/                                    # Dedicated Client AML Sentinel Engine (Slice S4)
│   │   ├── __init__.py                         # Package exports
│   │   ├── models.py                           # Pydantic v2 domain schemas (AMLAlert, RoundTrip, MuleRing, SAR)
│   │   ├── baseline.py                         # Pre-registered naive threshold rule baseline engine
│   │   ├── peer_baseline.py                    # Peer-group cohort baselines (cold start) + robust Z-scores
│   │   ├── triage_scorer.py                    # Supervised 2,000 -> 50 alert prioritizer & queue ranker
│   │   ├── roundtrip_detector.py               # Temporal sequence matcher: deposit -> micro-trade -> withdraw
│   │   ├── mule_ring_detector.py               # Bipartite NetworkX graph clustering & hub suppression
│   │   ├── withdrawal_sentinel.py              # Sub-2.0s real-time pre-withdrawal evaluation & KMS intent proposal
│   │   ├── sar_composer.py                     # Regulator-ready SAR narrative composer with statutory normalizer
│   │   ├── dossier.py                          # Multi-source evidence aggregator (5+ data products)
│   │   ├── emerging_typologies.py              # Unsupervised residual novelty miner for zero-day schemes
│   │   ├── feedback_loop.py                    # Analyst disposition ingestion & batch threshold recalibration
│   │   └── pipeline.py                         # Batch surveillance orchestrator populating DuckDB hot state
│   ├── conversation/
│   │   └── specialists/
│   │       └── aml.py                          # SentinelAMLSpecialist: OMCP-grounded domain agent with replay fallback
│   └── ontology/
│       └── omcp/
│           └── server.py                       # Canonical OMCP handlers: get_client_aml_dossier, etc.
```

---

## 5. Project Structure & Deliverables

### Documentation (`specs/010-client-aml/`)
```text
specs/010-client-aml/
├── plan.md                                     # This architectural implementation plan
├── research.md                                 # Technical trade-offs & algorithm selections
├── data-model.md                               # Pydantic v2 models & DuckDB DDL schemas
├── quickstart.md                               # End-to-end runnable validation guide
├── checklists/
│   └── requirements.md                         # Quality validation checklist
└── contracts/
    ├── aml-case-dossier.schema.json            # OMCP dossier response schema
    ├── mule-ring-cluster.schema.json           # OMCP mule ring cluster response schema
    ├── roundtrip-structuring-alerts.schema.json# OMCP roundtrip alerts response schema
    ├── withdrawal-risk-assessment.schema.json  # Pre-withdrawal risk check response schema
    └── sar-draft.schema.json                   # SAR draft filing response schema
```

### Test Suites (`FEIOS/tests/aml/`)
```text
FEIOS/tests/aml/
├── conftest.py                                 # Synthetic AML transactions & network fixtures
├── test_aml_eval.py                            # Blocking eval: triage scorer beats naive baseline >= 0.15 PR-AUC
├── test_triage_scorer.py                       # Unit tests: 2,000 -> 50 queue compression & feature weights
├── test_peer_baseline.py                       # Unit tests: cold-start cohort baselines vs. mature Z-scores
├── test_roundtrip_detector.py                  # Unit tests: 72h KYC recency, near-zero P&L, turnover velocity
├── test_mule_ring_detector.py                  # Unit tests: NetworkX clustering, hub suppression, Wi-Fi filtering
├── test_withdrawal_sentinel.py                 # Unit tests: < 2.0s latency, KMS-signed HoldWithdrawal proposal
├── test_sar_composer.py                        # Unit tests: FinCEN sections, citation coverage, statutory normalization
└── test_dossier_and_feedback.py                # Integration tests: 5+ source collation & analyst feedback loop
```

---

## 6. Implementation Phasing Strategy

### Phase 1: Setup & Domain Schemas
- Initialize package `FEIOS/src/eios/aml/__init__.py`.
- Define all domain entities in `FEIOS/src/eios/aml/models.py`.
- Configure test fixtures and synthetic transaction generators in `FEIOS/tests/aml/conftest.py`.

### Phase 2: Foundational Hot-State & Data Contracts
- Extend `HotStateEngine` in `FEIOS/src/eios/ingestion/hot_state.py` with tables:
  - `aml_alert_scores`
  - `aml_roundtrip_events`
  - `aml_mule_rings`
  - `aml_withdrawal_assessments`
  - `aml_case_dossiers`

### Phase 3: Detection Engines & Naive Baseline
- Implement pre-registered `NaiveThresholdBaseline` in `FEIOS/src/eios/aml/baseline.py`.
- Implement `PeerBaselineEngine` in `FEIOS/src/eios/aml/peer_baseline.py`.
- Implement `RoundTripDetector` in `FEIOS/src/eios/aml/roundtrip_detector.py`.
- Implement `MuleRingDetector` in `FEIOS/src/eios/aml/mule_ring_detector.py`.
- Implement `AlertTriageScorer` in `FEIOS/src/eios/aml/triage_scorer.py`.

### Phase 4: Real-Time Sentinel, Dossier, & SAR Composer
- Implement `WithdrawalSentinel` in `FEIOS/src/eios/aml/withdrawal_sentinel.py` (KMS ECDSA P-256 proposals).
- Implement `AMLDossierAssembler` in `FEIOS/src/eios/aml/dossier.py`.
- Implement `SARComposer` in `FEIOS/src/eios/aml/sar_composer.py` with statutory regex normalizer.
- Implement `AnalystFeedbackLoop` in `FEIOS/src/eios/aml/feedback_loop.py` and `EmergingTypologyMiner` in `FEIOS/src/eios/aml/emerging_typologies.py`.
- Implement batch pipeline `ClientAMLPipeline` in `FEIOS/src/eios/aml/pipeline.py`.

### Phase 5: OMCP Server Endpoints & Conversational Specialist
- Register 6 OMCP tool handlers in `FEIOS/src/eios/ontology/omcp/server.py`.
- Upgrade `SentinelAMLSpecialist` in `FEIOS/src/eios/conversation/specialists/aml.py`.
- Add batch CLI script `FEIOS/scripts/run_client_aml_pipeline.py`.
- Add withdrawal testing script `FEIOS/scripts/test_withdrawal_sentinel.py`.

### Phase 6: Verification & Eval Gates
- Verify blocking eval gate: `test_aml_eval.py` ($\ge 0.15$ PR-AUC delta, FPR reduction on hard negatives).
- Run full unit, contract, and integration test suite with coverage $\ge 80\%$.
- Verify full test regression suite across FEIOS.

---

## 7. Complexity Tracking

> **Constitution Invariant Compliance**: No ungrounded complexity or constitutional violations.

| Architectural Pattern | Why Needed | Alternative Rejected |
|---|---|---|
| Bipartite NetworkX with Hub Suppression | Eliminates false-merges across shared public Wi-Fi & CGNAT | Naive connected components falsely merged 1,000s of innocent users |
| Dual-Horizon Peer Cohort Baselines | Solves cold-start without alarming on every new deposit | Static global thresholds cause 95% false-positive rate |
| Cloud KMS Action Intent Tokens | Principle II: Non-repudiable human-governed proposals | Direct database updates violate irreversible compliance governance |
