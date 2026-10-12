# Quickstart Validation Guide: Closed-Loop Decision Learning Flywheel (014-flywheel)

**Feature**: Closed-Loop Decision Learning Flywheel & Counterfactual Causal Recalibration (`014-flywheel` / F13 / Slice S5)  
**Spec**: [`specs/014-flywheel/spec.md`](spec.md)  
**Data Model**: [`specs/014-flywheel/data-model.md`](data-model.md)  
**Contracts**: [`specs/014-flywheel/contracts/`](contracts/)  
**Status**: Ready for Planning & Implementation  

---

## 1. Prerequisites & Environment Setup

Verify the Python 3.11+ / uv virtual environment and existing feature test baselines:

```bash
cd "/Users/abdullahabtahi/Real-Time Enterprise Intelligence Agent/FEIOS"
uv run pytest tests/observability/ -q
```

---

## 2. End-to-End Validation Scenarios

### Scenario 1: Multi-Horizon Decision Outcomes Ledger & Reconciliation
**Objective**: Verify that action decisions are appended to the ledger with proposal propensity scores and reconciled against 30d, 60d, and 90d realized milestones.

```bash
uv run pytest tests/flywheel/test_outcomes_ledger.py -v
```
- **Expected Outcome**:
  - Emitted records conform to [`decision-outcome-record.schema.json`](contracts/decision-outcome-record.schema.json).
  - Propensity score $e(X)$ is locked at proposal time.
  - Residuals ($Y_{\text{actual}} - Y_{\text{pred}}$) are computed at each milestone without corrupting temporal alignment.

---

### Scenario 2: Doubly Robust AIPW Causal Uplift Estimator
**Objective**: Verify that the AIPW estimator reduces confounding-by-indication bias and accurately estimates Average Treatment Effects (ATE).

```bash
uv run pytest tests/flywheel/test_aipw_estimator.py -v
```
- **Expected Outcome**:
  - Emitted causal estimates conform to [`causal-uplift-estimate.schema.json`](contracts/causal-uplift-estimate.schema.json).
  - On confounded synthetic holdout datasets, AIPW recovers true treatment effect while naive difference-in-means exhibits severe bias (> 80% bias reduction).
  - Asymptotic standard error and 95% confidence intervals are strictly computed.

---

### Scenario 3: Causal-Evidence Gate Refuters (Constitution Principle III)
**Objective**: Verify that causal estimates are tested against placebo treatments, random common causes, and data subset stability checks.

```bash
uv run pytest tests/flywheel/test_causal_gate_refuters.py -v
```
- **Expected Outcome**:
  - Placebo treatment refuter produces $\hat{\tau}_{\text{placebo}} \approx 0$ with confidence interval spanning zero.
  - Random common cause refuter confirms stability ($< 10\%$ shift).
  - Estimates failing refuters or whose confidence intervals span zero are rejected from automated recalibration.

---

### Scenario 4: Offline SCM DAG Edge-Weight Recalibration
**Objective**: Verify offline re-estimation of Structural Causal Model DAG edge coefficients based on realized prediction residuals.

```bash
uv run pytest tests/flywheel/test_scm_dag_recalibration.py -v
```
- **Expected Outcome**:
  - Emitted DAG checkpoints conform to [`scm-recalibration-checkpoint.schema.json`](contracts/scm-recalibration-checkpoint.schema.json).
  - Updated edge weights reduce residual Mean Absolute Error (MAE).
  - Kahn's topological sort confirms DAG acyclicity is strictly preserved.

---

### Scenario 5: Playbook Policy Confidence & Prior Recalibration
**Objective**: Verify frontline action playbook confidence ratings and win-rates dynamically update based on empirical decision ledger evidence.

```bash
uv run pytest tests/flywheel/test_playbook_priors.py -v
```
- **Expected Outcome**:
  - Emitted policy priors conform to [`playbook-policy-prior.schema.json`](contracts/playbook-policy-prior.schema.json).
  - Successful interventions display increased empirical win-rates and narrowed confidence bounds.
  - Degraded interventions trigger uncertainty flags and rank downgrades.

---

### Scenario 6: Model Calibration Diagnostics, ECE & Drift Detection
**Objective**: Verify Expected Calibration Error (ECE) and Brier score evaluation with automated drift warnings feeding the Operations Workstation.

```bash
uv run pytest tests/flywheel/test_calibration_diagnostics.py -v
```
- **Expected Outcome**:
  - Diagnostics report conforms to [`calibration-diagnostics-report.schema.json`](contracts/calibration-diagnostics-report.schema.json).
  - Well-calibrated policies maintain $\text{ECE} < 0.10$.
  - Artificially miscalibrated policies ($\text{ECE} > 0.15$) trigger drift warning alerts.
  - Canonical OMCP tool `get_flywheel_calibration_status` returns complete platform diagnostics in under 200 ms.
