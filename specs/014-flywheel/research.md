# Technical Research & Architectural Decisions: Closed-Loop Decision Learning Flywheel (014-flywheel)

**Feature**: Closed-Loop Decision Learning Flywheel & Counterfactual Causal Recalibration (`014-flywheel` / F13 / Slice S5)  
**Spec**: [`specs/014-flywheel/spec.md`](spec.md)  
**Status**: Completed  
**Authoritative References**: `initial_plan.md` §3.1 (L5), §6.1, §12; `docs/engagement_plan.md` §2, §5 (Risk R12); `docs/models_and_evals.md`; `.specify/memory/constitution.md` (Principles I, II, III, V, VI, VII)

---

## 1. Context & Architectural Problem

In enterprise operational deployments, human operators selectively approve interventions on higher-risk accounts or high-value partners (e.g., AML freeze or proactive partner fee restructuring). This introduces **confounding by indication**:
- **The Pitfall**: Observational comparisons ($\mathbb{E}[Y \mid W=1] - \mathbb{E}[Y \mid W=0]$) are severely negatively biased because treated units were already in acute distress.
- **The Requirement**: Closed-loop learning must extract the true causal counterfactual treatment effect $\tau = Y(1) - Y(0)$ and recalibrate structural causal model (SCM) edge coefficients without operator-selection bias.

---

## 2. Architectural Decisions

### Decision 1: Doubly Robust Augmented Inverse Propensity Weighting (AIPW)
- **Decision**: Implement the Doubly Robust AIPW estimator with propensity clipping $[0.01, 0.99]$ and asymptotic influence-function variance estimation.
- **Mathematical Formulation**:
  $$\hat{\tau}_{\text{AIPW}} = \frac{1}{N} \sum_{i=1}^N \left( \hat{\mu}_1(X_i) - \hat{\mu}_0(X_i) + \frac{W_i(Y_i - \hat{\mu}_1(X_i))}{e(X_i)} - \frac{(1 - W_i)(Y_i - \hat{\mu}_0(X_i))}{1 - e(X_i)} \right)$$
  where:
  - $W_i \in \{0, 1\}$ is intervention assignment.
  - $Y_i$ is observed multi-horizon outcome (e.g., 60-day retained revenue or fraud recovered).
  - $X_i$ is pre-treatment context vector logged at proposal time.
  - $e(X_i) = P(W_i = 1 \mid X_i)$ is the proposing agent's propensity score, clipped to $[\epsilon, 1-\epsilon]$ ($\epsilon = 0.01$).
  - $\hat{\mu}_1(X) = \mathbb{E}[Y \mid W=1, X]$ and $\hat{\mu}_0(X) = \mathbb{E}[Y \mid W=0, X]$ are fitted outcome regressions.
- **Rationale**:
  - **Double Robustness Property**: If either the propensity model $e(X)$ OR the outcome regression $\mu(X)$ is correctly specified, the estimator remains unbiased and consistent.
  - Winsorization to $[0.01, 0.99]$ prevents unbounded variance when propensity scores approach 0 or 1.
- **Alternatives Considered**:
  - *Naive Difference-in-Means*: Rejected. Completely confounded by indication.
  - *Propensity Score Matching (PSM)*: Rejected. Prone to severe bias under small sample sizes and discards unmatched data.
  - *Pure Inverse Probability Weighting (IPW)*: Rejected. Extremely sensitive to propensity model misspecification.

---

### Decision 2: Causal-Evidence Gate Refuter Suite (Constitution Principle III)
- **Decision**: Integrate three automated causal refuters to validate AIPW estimates before certification:
  1. **Placebo Treatment Refuter**: Replaces treatment indicator $W$ with independent random noise $W_{\text{placebo}} \sim \text{Bernoulli}(0.5)$. Asserts that $\hat{\tau}_{\text{placebo}} \approx 0$ and its 95% confidence interval spans zero.
  2. **Random Common Cause Refuter**: Adds standard normal synthetic covariate $Z \sim \mathcal{N}(0, 1)$ to covariate matrix $X$. Asserts effect estimate change $|\hat{\tau}_{\text{new}} - \hat{\tau}| / |\hat{\tau}| \le 0.10$.
  3. **Data Subset Refuter**: Evaluates estimator on 80% bootstrap sub-samples. Asserts effect variation $\le 0.15$.
  4. **Strict Confidence Bound Gate**: The 95% confidence interval $[\hat{\tau} - 1.96 \cdot \text{SE}, \hat{\tau} + 1.96 \cdot \text{SE}]$ must strictly exclude zero for affirmative causal uplift claims.
- **Rationale**: Directly enforces Constitution Principle III ("A causal assertion MUST pass the gate... Otherwise the system MUST say 'correlation detected; insufficient evidence for causation'").
- **Alternatives Considered**:
  - *Unvalidated p-values*: Rejected. p-values alone do not guard against unobserved confounding or misspecification.

---

### Decision 3: Multi-Horizon Outcomes Ledger (30d / 60d / 90d)
- **Decision**: Store structured decision records in an in-memory/embedded table (`decision_outcomes_ledger`) capturing proposal-time context and multi-horizon outcome checkpoints.
- **Schema Columns**:
  - `decision_id` (UUID), `intent_id` (UUID), `timestamp` (UTC), `service_name`, `action_type`, `entity_id`.
  - `propensity_score` (float $0..1$), `covariates_json` (string).
  - `predicted_impact_30d`, `actual_impact_30d`, `residual_30d`, `status_30d` (`PENDING`, `RECORDED`, `RECONCILED`).
  - `predicted_impact_60d`, `actual_impact_60d`, `residual_60d`, `status_60d`.
  - `predicted_impact_90d`, `actual_impact_90d`, `residual_90d`, `status_90d`.
  - `provenance_hash` (SHA-256 digest over proposal + outcome).
- **Rationale**:
  - Provides a standardized, auditable ledger matching `initial_plan.md` §3.1 Layer 5 and `docs/engagement_plan.md`.
  - Supports both forward-simulated holdout testing (`docs/synthetic_data_strategy.md`) and production live streaming.

---

### Decision 4: SCM DAG Edge-Weight Recalibration Algorithm
- **Decision**: Implement an offline, regularized residual gradient update for Structural Causal Model DAG edge weights.
- **Mathematical Update Rule**:
  Given linear structural equation $Y_j = \sum_{k \in \text{pa}(j)} \beta_{kj} Y_k + \epsilon_j$:
  $$\beta_{kj}^{(t+1)} = \text{clip}\left(\beta_{kj}^{(t)} + \eta \cdot \frac{1}{N} \sum_{i=1}^N \text{residual}_{i,j} \cdot Y_{i,k} - \lambda \beta_{kj}^{(t)}, -2.0, 2.0\right)$$
  where $\eta = 0.1$ is the learning rate, $\lambda = 0.01$ is L2 shrinkage regularization, and edge weights are clipped to $[-2.0, 2.0]$.
- **Topology Check**:
  - Asserts that updated DAG maintains strictly positive variance and zero cycles via Kahn's topological sort algorithm.
  - Emits versioned checkpoint: `SCMRecalibrationCheckpoint`.
- **Rationale**: Satisfies Constitution Principle VII (offline batch decoupled execution). SCM weights update periodically without modifying code or blocking interactive turns.

---

### Decision 5: Expected Calibration Error (ECE) & Drift Alerting
- **Decision**: Partition probability predictions into $M=10$ equal-width bins $[0, 0.1), \dots, [0.9, 1.0]$ and calculate Expected Calibration Error and Brier Score:
  $$\text{ECE} = \sum_{m=1}^{10} \frac{|B_m|}{N} |\text{acc}(B_m) - \text{conf}(B_m)|$$
  $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$$
- **Alert Trigger**: If $\text{ECE} > 0.15$, trigger an operational drift warning exported to the Operations Board and SRE Alerting Engine.

---

### Decision 6: Preservation of Open Decisions (ADR-002, ADR-003, ADR-009, ADR-014)
- **Decision**: The flywheel module will remain purely domain-driven and technology-agnostic:
  - Model IDs and pricing remain configurable parameters (`ADR-002`).
  - No database engine or query dialect is hardcoded (`ADR-003`).
  - No frontend UI framework or bundling dependencies are introduced (`ADR-009`).
  - OMCP tools use standard dictionary/JSON contract interfaces without fixing HTTP vs. gRPC transports (`ADR-014`).
