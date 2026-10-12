# EIOS Partner Churn Radar (Module C / Slice S2)

> **Industry Benchmark Standard**: QuantumBlack Horizon Architecture × Palantir Foundry Kinetic Ontology & FDE Doctrine × Google Cloud Real-Time Financial Intelligence

The **Partner Churn Radar** is the enterprise predictive intelligence engine of the Forex Enterprise Intelligence Operating System (FEIOS). It transforms reactive relationship management into a governed, revenue-optimized operational system that prevents affiliate and introducing broker (IB) disengagement before it impacts net deposit volumes.

---

## 1. System Architecture & Constitutional Guarantees

```
                                 [L1 CANONICAL DATA PRODUCTS]
            DP6: partner_360  |  DP8: commission_ledger  |  DP9: partner_engagement_signals
            DP10: partner_comms | DP11: financial_pnl   |  DP12: competitor_benchmarks
                                              │
                                              ▼
                             [PartnerFeatureExtractor (T007)]
                           5 Signal Families Normalized Matrix
                                              │
                       ┌──────────────────────┴──────────────────────┐
                       ▼                                             ▼
          [SeasonalityChangePointDetector]            [DiscreteTimeHazardModel (T010)]
          Market Trading Calendar Masking             Logistic Hazard Link S(4)=Π(1-h_w)
          WoW CUSUM & Rolling Median MAD              Zero LLM Math (Principle I)
                       │                                             │
                       └──────────────────────┬──────────────────────┘
                                              ▼
                                 [ChurnRadarPipeline (T012)]
                                  Batch Scoring Coordinator
                                              │
                       ┌──────────────────────┼──────────────────────┐
                       ▼                      ▼                      ▼
           [Value-at-Risk Queue]   [CohortRiskDetector]    [ChurnSignalExplainer]
           Priority = Hazard * VaR  Permutation Test p<0.01  5-Family Attribution
                       │                      │                      │
                       ▼                      ▼                      ▼
         [DuckDB Hot State: churn_radar_scores, churn_cohort_alerts (Sub-5ms SLA)]
                                              │
                                              ▼
                             [OMCP Tool Server / Workshop Cockpit]
               get_partner_signals | get_high_risk_cohorts | propose_action
                                              │
                                              ▼
                           [ActionIntentHub (ECDSA P-256 KMS Signed)]
                                LaunchRetentionPlaybook
                                              │
                                              ▼
                           [Decision_Ledger & AIPW Flywheel (T029)]
                          Doubly Robust Causal Weight Recalibration
```

### Core Constitutional Invariants
- **Principle I (Zero LLM Metric Math)**: All hazard probabilities, priority scores, CUSUM MAD values, and AIPW causal estimators are computed in deterministic, vectorized Python (`scipy`, `numpy`, `sklearn`, `duckdb`). Large Language Models NEVER generate or calculate numbers.
- **Principle II (Non-Autonomous Governed Actions)**: Interventions require cryptographically signed `ActionIntentToken` proposals with Cloud KMS ECDSA P-256 signatures, 15-minute expiry nonces, and Four-Eyes state machine approval.
- **Principle VI (Eval-First CI Gate)**: Challenger model must strictly beat the pre-registered baseline ("no login > 14 days") by $\ge +0.10$ PR-AUC on sealed holdout evaluation (`test_churn_radar_eval.py`).
- **Principle VIII (Deterministic Replay Fallback)**: If external LLM gateways fail or are unreachable, cached golden templates marked with `[REPLAY]` badges are deterministically served.

---

## 2. Mathematical Formulations

### 2.1 Discrete-Time Hazard Model
Survival probability across four discrete weekly person-period intervals $t \in \{1, 2, 3, 4\}$:
$$\text{logit}(h_{it}) = \alpha_t + \boldsymbol{\beta}^T \mathbf{X}_{it}$$
$$S_i(4) = \prod_{w=1}^4 (1 - h_{iw})$$
$$P(\text{churn in 30d}) = 1 - S_i(4)$$
Priority ranking is evaluated as:
$$\text{Priority Score}_i = P(\text{churn in 30d})_i \times \text{Value-at-Risk}_{i}$$

### 2.2 Seasonality-Adjusted Anomaly Filtering (Zero False Alarms)
Trading-day masked Week-over-Week (WoW) ratio:
$$R_{i,w} = \frac{\sum_{d \in W_w} \text{Logins}_{i,d} + 1}{\sum_{d \in W_{w-1}} \text{Logins}_{i,d} + 1}$$
Filtered out if seasonal recovery occurs or holiday calendar matches, suppressing alerts on temporary vacations (`P-HARD-NEG-VACATION`, False Positive Rate $\le 5\%$).

### 2.3 Systemic Regional Cohort Permutation Test
Evaluates Binomial tail probability across active partners in region $r$:
$$P(X \ge K_r) = \sum_{k=K_r}^{N_r} \binom{N_r}{k} p_{\text{global}}^k (1 - p_{\text{global}})^{N_r - k}$$
If $p\text{-value} < 0.01$ and $K_r \ge 3$, suppresses individual alerts and emits a unified `CohortAnomalyAlert`.

### 2.4 Doubly Robust AIPW Causal Estimator
Eliminates confounding-by-indication when evaluating intervention efficacy:
$$\hat{\tau}_{\text{AIPW}} = \frac{1}{N} \sum_{i=1}^N \left[ \hat{\mu}_1(\mathbf{X}_i) - \hat{\mu}_0(\mathbf{X}_i) + \frac{W_i (Y_i - \hat{\mu}_1(\mathbf{X}_i))}{e(\mathbf{X}_i)} - \frac{(1 - W_i)(Y_i - \hat{\mu}_0(\mathbf{X}_i))}{1 - e(\mathbf{X}_i)} \right]$$

---

## 3. The Three Golden Test Personas

| Persona ID | Role | Baseline Trajectory | Planted Anomaly | Expected Model Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `P-CHURN-DRIFT` | **VIP Master IB (SEA)** | $45,000/mo commission, 80 clients | 40% WoW login decay, ticket citing rival broker 60% revshare | **HIGH Risk** (`hazard = 1.00`, `priority = $44,998`). Optimal intervention window. Cites competitive & behavioral drivers. |
| `P-HARD-NEG-VACATION` | **Tier-2 EU Affiliate** | $8,500/mo commission, 25 clients | Zero logins and clicks for 14 days during August holiday | **LOW Risk** (`hazard = 0.15`). Alert suppressed by seasonality filter. Zero false alarm. |
| `P-COHORT-SEA-CLUSTER` | **Regional SEA Cluster** | 15 Affiliates, $180,000/mo combined VaR | Synchronized FTD drop across Malaysia & Indonesia | **Systemic Cohort Alert** (`p-value < 0.0001`). Recommends regional affiliate incentive playbook. |

---

## 4. Operational Commands & Demo Scripts

### Running the Evaluation Gate (CI Gate)
```bash
pytest tests/churn/test_churn_radar_eval.py -v
```

### Running the Operational Cockpit Live Demo
```bash
python scripts/run_churn_pipeline.py --demo-mode
```

### Running the Governed Action & Causal Flywheel Demo
```bash
python scripts/test_retention_intent.py
```

### Running the GenAI Emerging Pattern Discovery Demo
```bash
python scripts/test_churn_pattern_discovery.py
```

### Running the Full Test Suite with Coverage
```bash
pytest tests/churn --cov=eios.churn
```
*(Guaranteed 100% test pass, $\ge 85\%$ line coverage across all churn modules).*
