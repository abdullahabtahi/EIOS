# Tasks: Partner & Affiliate Fraud Sentinel (Module B / Slice S3)

**Input**: Design documents from `/specs/009-partner-fraud/` (`spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)  
**Authoritative References**: `docs/brief/fraud` `[BRIEF fraud]`, `initial_plan.md` §5.3, `docs/models_and_evals.md` §4, `.specify/memory/constitution.md`  
**Prerequisites**: Virtualenv active (`FEIOS/.venv/bin/python`), DuckDB hot-state engine, registered OMCP tools.  

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (`[US1]` through `[US7]`), omitted for Setup, Foundational, and Polish phases
- All tasks specify exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure & Domain Schemas)

**Purpose**: Package initialization, domain models, and synthetic test fixtures

- [x] T001 Initialize partner fraud package structure in FEIOS/src/eios/fraud/__init__.py
- [x] T002 [P] Create Pydantic v2 domain schemas (TradingPairCorrelation, ReferralRingNode, RingAttribution, BonusAbuseProfile, RecyclingCluster, TrafficAnomalySignal, PartnerFraudCase) in FEIOS/src/eios/fraud/models.py
- [x] T003 [P] Configure synthetic fraud cohort generators and test fixtures (collusive pairs, 3-tier sub-affiliate trees, bonus harvesting accounts, recycling identity tokens, bot traffic streams) in FEIOS/tests/fraud/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core hot-state storage, naive baseline, blocking eval gate, and compliance sanitization  
**⚠️ CRITICAL**: Must complete before user story implementation begins

- [x] T004 Setup DuckDB analytical DDL schemas (partner_fraud_scores, partner_opposite_trading_pairs, partner_fraud_cases) in FEIOS/src/eios/ingestion/hot_state.py
- [x] T005 [P] Implement pre-registered naive threshold rule baseline detector (opposite direction within 30s) in FEIOS/src/eios/fraud/baseline.py
- [x] T006 [P] Implement blocking eval-first test asserting multi-factor detector beats naive baseline by >= 0.15 PR-AUC on sealed holdouts in FEIOS/tests/fraud/test_fraud_eval.py
- [x] T007 [P] Implement semantic egress gate sanitization rule mapping inflammatory allegations to objective compliance inquiry phrasing in FEIOS/src/eios/fraud/sanitizer.py

**Checkpoint**: Foundation ready - hot state initialized, baseline established, blocking eval gate active.

---

## Phase 3: User Story 1 - Coordinated Opposite & Mirror Trading Pair Detection (Priority: P1) 🎯 MVP

**Goal**: Detect pairs of accounts across distinct affiliates taking inverse or lockstep positions within sliding execution windows with zero-sum P&L extraction  
**Independent Test**: Run `pytest FEIOS/tests/fraud/test_pair_detector.py` and `pytest FEIOS/tests/fraud/test_pair_contract.py`; verify detector flags planted opposite/mirror pairs with >= 90% recall and keeps FPR < 5% on legitimate hedgers.

### Tests for User Story 1 (Eval-First) ⚠️
- [x] T008 [P] [US1] Write unit and contract tests for sliding 30s bucket partitioning, directional anti-correlation, volume symmetry, and zero-sum P&L extraction in FEIOS/tests/fraud/test_pair_detector.py
- [x] T009 [P] [US1] Write contract validation test for opposite-trading-pairs.schema.json in FEIOS/tests/fraud/test_pair_contract.py

### Implementation for User Story 1
- [x] T010 [US1] Implement time-bucketed candidate hashing and indexing over trading logs in FEIOS/src/eios/fraud/pair_detector.py
- [x] T011 [US1] Implement bilateral correlation metrics (directional correlation, volume symmetry, exponential timing score exp(-delta_t / tau), zero-sum P&L ratio) in FEIOS/src/eios/fraud/pair_detector.py
- [x] T012 [US1] Implement composite collusion scoring and legitimate hedger filtering (FPR < 5%) in FEIOS/src/eios/fraud/pair_detector.py
- [x] T013 [US1] Implement DuckDB hot-state batch persistence for identified trading pairs in FEIOS/src/eios/fraud/pair_detector.py

**Checkpoint**: User Story 1 (MVP) fully functional, testable independently, and passing evaluation criteria.

---

## Phase 4: User Story 2 - Multi-Tier Sub-Affiliate Ring Mapping & Master Partner Attribution (Priority: P1)

**Goal**: Map 3-layer sub-affiliate network hierarchies, detect circular loops, suppress legitimate broker hubs, and attribute aggregate ring exposure back to root Master Partner  
**Independent Test**: Run `pytest FEIOS/tests/fraud/test_ring_attribution.py` and `pytest FEIOS/tests/fraud/test_ring_contract.py`; verify >= 95% recovery of root master partner in 3-tier synthetic trees without penalizing legitimate high-degree IBs.

### Tests for User Story 2 (Eval-First) ⚠️
- [x] T014 [P] [US2] Write unit and contract tests for 3-tier NetworkX referral graph traversal, hub suppression, cycle detection, and master attribution in FEIOS/tests/fraud/test_ring_attribution.py
- [x] T015 [P] [US2] Write contract validation test for referral-ring-attribution.schema.json in FEIOS/tests/fraud/test_ring_contract.py

### Implementation for User Story 2
- [x] T016 [US2] Implement directed hierarchical referral tree builder with cycle detection and loop breaking in FEIOS/src/eios/fraud/ring_attribution.py
- [x] T017 [US2] Implement degree-penalized hub suppression to prevent legitimate high-volume IBs from false ring clustering in FEIOS/src/eios/fraud/ring_attribution.py
- [x] T018 [US2] Implement upstream master partner attribution and aggregate ring financial exposure calculation in FEIOS/src/eios/fraud/ring_attribution.py

**Checkpoint**: User Story 2 fully functional and independently verified on 3-tier referral hierarchies.

---

## Phase 5: User Story 3 - Client Quality & Bonus Abuse Scoring (Priority: P1)

**Goal**: Detect deposit -> micro-trade -> immediate withdrawal bonus harvesting and compute the composite Client Quality Index (CQI) per partner  
**Independent Test**: Run `pytest FEIOS/tests/fraud/test_bonus_abuse.py` and `pytest FEIOS/tests/fraud/test_bonus_contract.py`; verify partners with > 70% 72-hour withdrawals receive CQI < 0.20 and HIGH_BONUS_ABUSE_RISK flag.

### Tests for User Story 3 (Eval-First) ⚠️
- [x] T019 [P] [US3] Write unit and contract tests for client lifecycle velocity, micro-trading frequency, fast withdrawals, and CQI in FEIOS/tests/fraud/test_bonus_abuse.py
- [x] T020 [P] [US3] Write contract validation test for client-quality-profile.schema.json in FEIOS/tests/fraud/test_bonus_contract.py

### Implementation for User Story 3
- [x] T021 [US3] Implement per-client lifecycle velocity feature extraction (deposit-to-withdrawal latency, turnover ratio, 30-day retention) in FEIOS/src/eios/fraud/bonus_abuse.py
- [x] T022 [US3] Implement partner-level Client Quality Index (CQI) and composite bonus abuse probability calculation in FEIOS/src/eios/fraud/bonus_abuse.py
- [x] T023 [US3] Implement affiliate tiering risk classification (NORMAL, MONITORING, HIGH_BONUS_ABUSE_RISK) in FEIOS/src/eios/fraud/bonus_abuse.py

**Checkpoint**: User Story 3 fully functional; automated CQI and bonus abuse risk scoring operational.

---

## Phase 6: User Story 4 - Identity Clustering & Cross-Affiliate Client Recycling Detection (Priority: P2)

**Goal**: Group cross-affiliate accounts sharing pseudonymized Identity Cluster Keys (`tok_id_cluster_<hex16>`) to identify syndicate promotion recycling without PII exposure  
**Independent Test**: Run `pytest FEIOS/tests/fraud/test_recycling_detector.py`; verify accounts sharing identity keys across distinct partner IDs are clustered while distinguishing shared household/corporate IPs.

### Tests for User Story 4 (Eval-First) ⚠️
- [x] T024 [P] [US4] Write unit tests for pseudonymized identity cluster token matching across distinct partner IDs in FEIOS/tests/fraud/test_recycling_detector.py

### Implementation for User Story 4
- [x] T025 [US4] Implement bipartite graph builder mapping tok_id_cluster_<hex16> entity keys across partner referral hierarchies in FEIOS/src/eios/fraud/recycling_detector.py
- [x] T026 [US4] Implement recycling syndicate identification, promotion harvesting aggregation, and cross-affiliate overlap quantification in FEIOS/src/eios/fraud/recycling_detector.py
- [x] T027 [US4] Add household and corporate shared network distinction logic to bound false positive syndicate alarms in FEIOS/src/eios/fraud/recycling_detector.py

**Checkpoint**: User Story 4 operational with privacy-preserving identity token clustering.

---

## Phase 7: User Story 5 - Traffic & Bot Anomaly Detection (Priority: P2)

**Goal**: Identify unnatural click-to-lead-to-deposit conversion funnels, stolen leads, and bot-driven traffic exceeding peer benchmarks by > 3.0 sigma  
**Independent Test**: Run `pytest FEIOS/tests/fraud/test_traffic_anomaly.py`; verify synthetic bot funnels with 90%+ click-to-FTD conversion are flagged with p < 0.001 while allowing organic seminar spikes.

### Tests for User Story 5 (Eval-First) ⚠️
- [x] T028 [P] [US5] Write unit tests for Beta-Binomial conversion dispersion, peer cohort statistical outliers, and bot traffic probability in FEIOS/tests/fraud/test_traffic_anomaly.py

### Implementation for User Story 5
- [x] T029 [US5] Implement Beta-Binomial peer cohort conversion benchmark model (click-to-signup, signup-to-FTD) in FEIOS/src/eios/fraud/traffic_anomaly.py
- [x] T030 [US5] Implement empirical Bayes dispersion test, p-value calculation (p < 0.001), and registration-to-deposit latency variance check in FEIOS/src/eios/fraud/traffic_anomaly.py
- [x] T031 [US5] Implement contextual offline seminar and marketing campaign variance justification handler in FEIOS/src/eios/fraud/traffic_anomaly.py

**Checkpoint**: User Story 5 operational; bot and traffic anomalies statistically quantified.

---

## Phase 8: User Story 6 - Explainable Investigation Dossier & Governed Action Intent Proposals (Priority: P2)

**Goal**: Assemble multi-source investigation dossiers and emit Cloud KMS ECDSA P-256 signed Action Intent proposals (ClawbackCommission, SuspendPartner) under dual four-eyes approval  
**Independent Test**: Run `pytest FEIOS/tests/fraud/test_dossier_and_actions.py` and `pytest FEIOS/tests/ontology/test_omcp_partner_fraud_tools.py`; verify complete dossier assembly in < 2.5s and strict FourEyesApprovalRequiredError enforcement.

### Tests for User Story 6 (Eval-First) ⚠️
- [x] T032 [P] [US6] Write integration tests for investigation dossier assembly, KMS ECDSA P-256 token signing, and dual four-eyes approval enforcement in FEIOS/tests/fraud/test_dossier_and_actions.py
- [x] T033 [P] [US6] Write contract validation test for fraud-case-dossier.schema.json in FEIOS/tests/fraud/test_dossier_contract.py

### Implementation for User Story 6
- [x] T034 [US6] Implement multi-source evidence synthesis assembler and executive dossier builder in FEIOS/src/eios/fraud/dossier.py
- [x] T035 [US6] Register canonical Action Specs ClawbackCommission and SuspendPartner with mandatory dual four-eyes approval (requires_dual_approval = True) in FEIOS/src/eios/ontology/actions/intent_hub.py
- [x] T036 [US6] Implement canonical OMCP tool handlers (get_opposite_trading_pairs, get_partner_referral_ring, get_client_quality_profile, get_partner_fraud_dossier) in FEIOS/src/eios/ontology/omcp/server.py
- [x] T037 [US6] Write integration test suite verifying all 4 OMCP tool endpoints against schema contracts in FEIOS/tests/ontology/test_omcp_partner_fraud_tools.py

**Checkpoint**: User Story 6 complete; OMCP tool endpoints and governed non-autonomous action intents fully operational.

---

## Phase 9: User Story 7 - Unsupervised Emerging Fraud Scheme Discovery & Temporal Intelligence (Priority: P3)

**Goal**: Uncover novel unlabelled fraud typologies and track partner behavioral shifts, pre-fraud signatures, and escalation velocity over time  
**Independent Test**: Run `pytest FEIOS/tests/fraud/test_emerging_patterns.py`; verify unsupervised sub-graph miner isolates cyclic commission rebating and flags partner behavior drift within 6-week observation windows.

### Tests for User Story 7 (Eval-First) ⚠️
- [x] T038 [P] [US7] Write unit tests for unsupervised anomaly sub-graph mining, temporal drift detection, and novel typology isolation in FEIOS/tests/fraud/test_emerging_patterns.py

### Implementation for User Story 7
- [x] T039 [US7] Implement unsupervised graph clustering and transaction distribution anomaly miner in FEIOS/src/eios/fraud/emerging_patterns.py
- [x] T040 [US7] Implement temporal intelligence analyzer detecting partner behavioral shifts, pre-fraud signatures, and escalation velocity in FEIOS/src/eios/fraud/emerging_patterns.py

**Checkpoint**: User Story 7 operational; unsupervised discovery and temporal pattern analysis active.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Pipeline coordination, conversational agent integration, batch runners, and full regression verification

- [x] T041 [P] Implement batch pipeline coordinator orchestrating pair detection, ring attribution, CQI, bot traffic, and DuckDB table updates in FEIOS/src/eios/fraud/pipeline.py
- [x] T042 [P] Implement PartnerFraudSpecialist conversational subagent with deterministic replay fallback and semantic egress gate in FEIOS/src/eios/conversation/specialists/fraud.py
- [x] T043 Register PartnerFraudSpecialist in SupervisoryRouter dispatcher in FEIOS/src/eios/conversation/router.py
- [x] T044 [P] Create runnable end-to-end batch script in FEIOS/scripts/run_partner_fraud_pipeline.py
- [x] T045 [P] Create runnable action intent verification script in FEIOS/scripts/test_partner_fraud_intent.py
- [x] T046 Run full pytest suite ensuring >= 80% coverage and verify all 2,075 existing tests continue passing
- [x] T047 Validate all quickstart scenarios in specs/009-partner-fraud/quickstart.md and verify zero unlabelled numbers via tests/governance/test_label_check_f00_docs.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3 through Phase 9)**: All depend on Foundational phase completion
  - **US1 (P1 - MVP)**: Can start immediately after Phase 2
  - **US2 (P1)**: Can start after Phase 2; consumes partner network graph
  - **US3 (P1)**: Can start after Phase 2; consumes trading and deposit lifecycles
  - **US4 (P2)**: Can start after Phase 2; consumes identity cluster keys
  - **US5 (P2)**: Can start after Phase 2; consumes clickstream and conversions
  - **US6 (P2)**: Depends on US1, US2, and US3 outputs for full dossier assembly
  - **US7 (P3)**: Depends on US1 and US2 graph structures for unsupervised mining
- **Polish (Phase 10)**: Depends on completion of user stories

### Parallel Opportunities

- **Phase 1**: T002 and T003 can run in parallel
- **Phase 2**: T005, T006, and T007 can run in parallel after T004
- **Phase 3 (US1)**: T008 and T009 test tasks run in parallel; T010, T011, T012, T013 run sequentially
- **Phase 4 (US2)**: T014 and T015 test tasks run in parallel; T016, T017, T018 run sequentially
- **Phase 5 (US3)**: T019 and T020 test tasks run in parallel; T021, T022, T023 run sequentially
- **Phase 6 (US4)**: T024 can run in parallel with other story tests
- **Phase 7 (US5)**: T028 can run in parallel with other story tests
- **Phase 8 (US6)**: T032 and T033 run in parallel; T034, T035, T036, T037 execute sequentially
- **Phase 9 (US7)**: T038 can run in parallel with other story tests
- **Phase 10**: T041, T042, T044, T045 can run in parallel

---

## Parallel Example: User Story 1 (MVP)

```bash
# Launch test definitions in parallel:
Task: "T008 [P] [US1] Write unit and contract tests in FEIOS/tests/fraud/test_pair_detector.py"
Task: "T009 [P] [US1] Write contract validation test in FEIOS/tests/fraud/test_pair_contract.py"

# After tests fail (red), execute implementation sequentially:
Task: "T010 [US1] Implement time-bucketed candidate hashing in FEIOS/src/eios/fraud/pair_detector.py"
Task: "T011 [US1] Implement bilateral correlation metrics in FEIOS/src/eios/fraud/pair_detector.py"
Task: "T012 [US1] Implement composite collusion scoring in FEIOS/src/eios/fraud/pair_detector.py"
Task: "T013 [US1] Implement DuckDB persistence in FEIOS/src/eios/fraud/pair_detector.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`FEIOS/src/eios/fraud/models.py`, `conftest.py`)
2. Complete Phase 2: Foundational (`hot_state.py`, `baseline.py`, `test_fraud_eval.py`)
3. Complete Phase 3: User Story 1 (`pair_detector.py`, `test_pair_detector.py`)
4. **STOP and VALIDATE**: Verify pair detector beats naive baseline by $\ge 0.15$ PR-AUC on sealed seeds.

### Incremental Delivery

1. Setup + Foundation $\to$ Baseline eval active
2. Add US1 (Opposite Trading) $\to$ MVP ready!
3. Add US2 (3-Tier Ring Attribution) $\to$ Master Partner attribution operational
4. Add US3 (Bonus Abuse & CQI) $\to$ Client quality scoring operational
5. Add US4 (Identity Recycling) $\to$ Privacy-preserving multi-account syndicate clustering
6. Add US5 (Bot & Traffic Fraud) $\to$ Funnel anomaly detection active
7. Add US6 (Investigation Dossier & Governed Actions) $\to$ OMCP tool surface & dual four-eyes approval active
8. Add US7 (Emerging Patterns & Temporal Intelligence) $\to$ Unsupervised discovery active
9. Polish & Full Regression $\to$ 100% test pass rate across 2,075+ tests maintained
