# Implementation Plan: Partner & Affiliate Fraud Sentinel (Module B / Slice S3)

**Branch**: `009-partner-fraud` | **Date**: 2026-10-07 | **Spec**: [specs/009-partner-fraud/spec.md](spec.md)

**Input**: Feature specification from `specs/009-partner-fraud/spec.md`, `initial_plan.md` §5.3, `docs/brief/fraud` `[BRIEF fraud]`, `docs/models_and_evals.md` §4, `.specify/memory/constitution.md`.

---

## 1. Summary

Deliver **Module B: Partner & Affiliate Fraud Sentinel** (completing Slice S3), operationalizing relational and network-based financial crime detection across 5,000 active affiliates for the Deriv Enterprise Intelligence Operating System. The architecture implements a **Time-Bucketed Pair Correlation Detector** over client trading portfolios to unmask coordinated opposite and mirror trading rings, coupled with a **Degree-Penalized NetworkX Referral Traversal Engine** that maps sub-affiliate structures up to 3 layers deep and attributes illicit commission volume back to the root Master Partner.

It features a deterministic **Client Quality & Bonus Abuse Scorer** evaluating deposit-to-withdrawal velocity, an **Identity Token Recycling Detector** that groups cross-affiliate accounts via pseudonymized `tok_id_cluster_<hex16>` keys, a **Beta-Binomial Traffic Anomaly Detector** flagging bot-driven conversion funnels, and an explainable **Investigation Dossier Engine**. All enforcement actions (`ClawbackCommission`, `SuspendPartner`) emit Cloud KMS ECDSA P-256 signed `ActionIntentToken` proposals subject to dual four-eyes human approval and recorded in the append-only `Decision_Ledger`, strictly honoring Constitution Principles I–VIII.

---

## 2. Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**:
- `networkx>=3.2.0` (Directed referral tree traversal, degree-penalized hub suppression, cycle detection)
- `pandas>=2.2.0`, `numpy>=1.26.0`, `scipy>=1.13.0` (Sliding time-bucket indexing, Pearson/Spearman anti-correlation, Beta-Binomial dispersion)
- `duckdb>=1.1.0` (In-process columnar hot-state analytical engine)
- `pydantic>=2.13.5` (Strict domain schemas and JSON schema contract enforcement)
- `cryptography>=42.0.0` (ECDSA P-256 KMS mock signatures and verification)
- `langgraph>=0.2.0` (Integration with Supervisory Router and Blackboard architecture)

**Storage**:
- In-process DuckDB Hot State (`HotStateEngine`) hosting `partner_fraud_scores`, `partner_opposite_trading_pairs`, and `partner_fraud_cases`
- Append-only `Decision_Ledger` simulated sink with atomic `ledger_seq` counter and SHA-256 hash chaining

**Testing**:
- `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`
- Sealed holdout evaluation comparing multi-factor pair detector against pre-registered naive rule baseline (`tests/fraud/test_fraud_eval.py`)

**Target Platform**: Linux Server / macOS / Google Cloud Run worker  
**Performance Goals**:
- Batch Candidate Pruning & Pair Correlation: $< 25\text{s}$ for 500,000 trade events `[TARGET]`
- Sub-Affiliate 3-Layer Graph Traversal & Master Attribution: $< 15\text{ms}$ per network query `[TARGET]`
- Online OMCP Tool Query Latency (`get_partner_fraud_dossier`): $< 50\text{ms}$ p95 from DuckDB hot state `[TARGET]`
- Memory Footprint: Bounded hot state with sliding-window pruning ($< 500\text{MB}$) `[TARGET]`

**Constraints**:
- **Constitution Principle I**: Zero LLM metric math (all correlation metrics, exposure sums, and quality indices calculated deterministically) `[TARGET]`
- **Constitution Principle II**: Zero autonomous write-back (all enforcement actions require KMS-signed proposals and dual four-eyes approval) `[TARGET]`
- **Constitution Principle IV**: All analytical data consumed strictly via OMCP tools and canonical L1 Data Products; PII strictly pseudonymized via `tok_id_cluster_<hex16>`
- **Constitution Principle VI**: Pair detector must beat pre-registered naive rule baseline by $\ge 0.15$ PR-AUC on sealed seeds
- **Constitution Principle VIII**: Deterministic replay fallback with `[REPLAY]` badges for all LLM narrative summaries

---

## 3. Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (LLMs Never Compute Metrics)**: PASS. All correlation coefficients, timing deltas, zero-sum ratios, network exposures, and quality indices are computed by deterministic Python algorithms (`scipy`, `numpy`, `networkx`). LLMs are strictly confined to narrative phrasing and evidence citation.
- **Principle II (No Autonomous Write-Back)**: PASS. Interventions are proposed as KMS-signed `ActionIntentToken` objects (`ClawbackCommission`, `SuspendPartner`) requiring 2 distinct human approvers before execution against the simulated sink.
- **Principle III (Honest Uncertainty & Causal Gate)**: PASS. Pair collusion and bot traffic flags cite statistical confidence intervals and p-values ($p < 0.001$). Ambiguous patterns emit "insufficient correlation evidence" warnings.
- **Principle IV (Ontology-Only Access)**: PASS. All inputs derive from canonical L1 Data Products (`partner_360`, `partner_network`, `trading_activity`, `commission_ledger`, `transactions_aml`, `clickstream`). Raw PII is never exposed; entity clusters use `tok_id_cluster_<hex16>`.
- **Principle V (Provenance & Labelling)**: PASS. All claims cite specific trade IDs and timestamps. Numbers carry `[TARGET]`, `[ASSUMPTION]`, or `[BRIEF fraud]` provenance tags.
- **Principle VI (Eval-First & Baselines)**: PASS. A naive threshold rule baseline ("opposite direction within 30s") is implemented first and must be beaten by $\ge 0.15$ PR-AUC on sealed holdout seeds.
- **Principle VII (Decoupled Pipelines & Specialized Agents)**: PASS. Batch fraud scoring runs independently of real-time query serving. Conversational queries route through `PartnerFraudSpecialist`.
- **Principle VIII (Deterministic Fallback)**: PASS. If external LLM calls fail, case summaries degrade to deterministic golden template fallbacks with `[REPLAY]` badges.

---

## 4. Architecture & Component Topology

```text
FEIOS/
├── src/eios/
│   ├── fraud/                                  # Dedicated Partner Fraud Sentinel Engine (Slice S3)
│   │   ├── __init__.py                         # Package exports
│   │   ├── models.py                           # Pydantic v2 domain schemas (TradingPair, RingNode, Case)
│   │   ├── pair_detector.py                    # Time-bucket candidate pruning & anti-correlation filter
│   │   ├── ring_attribution.py                 # NetworkX 3-layer sub-affiliate tree traversal & hub suppression
│   │   ├── bonus_abuse.py                      # Lifecycle velocity & Client Quality Index (CQI) scorer
│   │   ├── recycling_detector.py               # Identity cluster token matching across partner IDs
│   │   ├── traffic_anomaly.py                  # Beta-Binomial peer cohort conversion dispersion test
│   │   ├── baseline.py                         # Pre-registered naive threshold rule baseline engine
│   │   ├── dossier.py                          # Evidence synthesis & case briefing assembler
│   │   └── pipeline.py                         # Batch coordinator populating DuckDB hot state tables
│   ├── conversation/
│   │   └── specialists/
│   │       └── fraud.py                        # PartnerFraudSpecialist: OMCP-grounded domain agent
│   └── ontology/
│       ├── core/
│       │   └── objects.py                      # Extended Partner object with fraud risk properties
│       ├── functions/
│       │   └── partner.py                      # Registered ontology function get_partner_fraud_profile
│       └── omcp/
│           └── server.py                       # Canonical OMCP handlers: get_partner_fraud_dossier, etc.
```

---

## 5. Project Structure & Deliverables

### Documentation (`specs/009-partner-fraud/`)
```text
specs/009-partner-fraud/
├── plan.md                                     # This architectural implementation plan
├── research.md                                 # Technical trade-offs & algorithm selections
├── data-model.md                               # Pydantic v2 models & DuckDB DDL schemas
├── quickstart.md                               # End-to-end runnable validation guide
├── checklists/
│   └── requirements.md                         # Quality validation checklist
└── contracts/
    ├── fraud-case-dossier.schema.json          # OMCP dossier response schema
    ├── opposite-trading-pairs.schema.json      # OMCP opposite pairs response schema
    ├── referral-ring-attribution.schema.json   # OMCP referral tree response schema
    └── client-quality-profile.schema.json      # OMCP client quality response schema
```

### Test Suites (`FEIOS/tests/fraud/`)
```text
FEIOS/tests/fraud/
├── conftest.py                                 # Synthetic trading & referral ring fixtures
├── test_fraud_eval.py                          # Blocking eval: pair detector beats naive baseline >= 0.15 PR-AUC
├── test_pair_detector.py                       # Unit tests: time-bucketing, correlation, zero-sum P&L
├── test_ring_attribution.py                    # Unit tests: 3-tier NetworkX traversal, hub suppression, master link
├── test_bonus_abuse.py                         # Unit tests: lifecycle velocity, CQI, micro-trading
├── test_recycling_detector.py                  # Unit tests: identity cluster token matching
├── test_traffic_anomaly.py                     # Unit tests: Beta-Binomial conversion dispersion
└── test_dossier_and_actions.py                 # Integration tests: case dossier & KMS Action Intent tokens
```

---

## 6. Implementation Phasing Strategy

### Phase 1: Setup & Domain Schemas
- Initialize package `FEIOS/src/eios/fraud/__init__.py`.
- Define all domain entities in `FEIOS/src/eios/fraud/models.py`.
- Configure test fixtures and synthetic test trees in `FEIOS/tests/fraud/conftest.py`.

### Phase 2: Foundational Hot-State & Data Contracts
- Extend `HotStateEngine` in `FEIOS/src/eios/ingestion/hot_state.py` with tables:
  - `partner_fraud_scores`
  - `partner_opposite_trading_pairs`
  - `partner_fraud_cases`
- Implement pre-registered naive rule baseline in `FEIOS/src/eios/fraud/baseline.py`.
- Create blocking eval-first test in `FEIOS/tests/fraud/test_fraud_eval.py`.

### Phase 3: User Story 1 - Opposite & Mirror Trading Pair Detector (P1 - MVP)
- Implement sliding 30s bucket partitioning in `FEIOS/src/eios/fraud/pair_detector.py`.
- Implement directional anti-correlation, volume symmetry, and zero-sum P&L scoring.
- Verify pair detector beats naive baseline by $\ge 0.15$ PR-AUC on sealed holdouts.

### Phase 4: User Story 2 - Multi-Tier Ring Mapping & Master Attribution (P1)
- Implement 3-layer directed graph constructor in `FEIOS/src/eios/fraud/ring_attribution.py`.
- Implement degree-penalized hub suppression and cycle detection.
- Implement master partner exposure rollup.

### Phase 5: User Story 3 - Client Quality & Bonus Abuse Scorer (P1)
- Implement lifecycle velocity calculation in `FEIOS/src/eios/fraud/bonus_abuse.py`.
- Implement composite Client Quality Index (CQI).

### Phase 6: User Story 4 - Identity Clustering & Client Recycling (P2)
- Implement identity token matching engine in `FEIOS/src/eios/fraud/recycling_detector.py`.
- Unmask multi-partner syndicates sharing `tok_id_cluster_<hex16>`.

### Phase 7: User Story 5 - Traffic & Bot Anomaly Detection (P2)
- Implement Beta-Binomial conversion dispersion model in `FEIOS/src/eios/fraud/traffic_anomaly.py`.

### Phase 8: User Story 6 - Dossier Assembly & Governed Action Intents (P2)
- Implement evidence synthesis in `FEIOS/src/eios/fraud/dossier.py`.
- Register canonical action specs `ClawbackCommission` and `SuspendPartner` with dual four-eyes approval in `ActionIntentHub`.
- Implement OMCP tool handlers in `FEIOS/src/eios/ontology/omcp/server.py`.

### Phase 9: Polish & Full Verification
- Integrate `PartnerFraudSpecialist` into conversation mesh.
- Implement end-to-end pipeline runner in `FEIOS/scripts/run_partner_fraud_pipeline.py`.
- Run complete test suite and verify 100% pass rate.
