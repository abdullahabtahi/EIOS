# Implementation Plan: Executive Synthesis Engine (F05)

**Branch**: `006-synthesis-engine` | **Date**: 2026-10-06 | **Spec**: [specs/006-synthesis-engine/spec.md](spec.md)

**Input**: Feature specification from `specs/006-synthesis-engine/spec.md`, `specs/006-synthesis-engine/research.md`, `docs/brief/data.md`, `docs/models_and_evals.md` §5, and `FEIOS/docs/spikes_and_adrs.md` (ADR-005, S-04).

---

## Summary

Deliver the **Executive Synthesis Engine** (Slice S1 / F05) providing cross-domain causal intelligence across Competitive, Partner, Client, and Financial domains. The system decouples offline nightly SCM fitting and DoWhy-style refutation caching (`SCMCache`) from online sub-second parametric shock propagation per Spike S-04 / ADR-005 `[SPIKE]`. It implements a multivariate forecasting engine beating the seasonal-naive $y_{t-28}$ benchmark with $\text{MASE} < 1.0$ `[TARGET]` with strictly $100.0\% \pm 0.001\%$ additive driver attribution `[TARGET]`, a proactive daily Morning Briefing generator with cached replay fallback `[BRIEF]`, and a governed recommendation composer that logs propensity scores $e(X)$ to enable Doubly Robust AIPW offline causal flywheel recalibration `[TARGET]`.

---

## Technical Context

**Language/Version**: Python 3.14+  
**Primary Dependencies**: `duckdb>=1.1.0`, `networkx>=3.2.0`, `numpy>=1.26.0`, `polars>=0.20.0`, `pydantic>=2.13.5`, `pyyaml>=6.0.3`, `cryptography>=43.0.0`, `fastapi>=0.142.2`  
**Storage**: In-memory hot state (`HotStateEngine`), DuckDB in-process semantic engine, JSON/Parquet `SCMCache`, and append-only decision ledger  
**Testing**: `pytest`, `pytest-cov`, `pytest-xdist` with $\ge 80\%$ line and branch coverage gate `[TARGET]`  
**Target Platform**: Linux server / macOS / Cloud Run  
**Performance Goals**:
- Online `get_causal_chain` retrieval: $< 100\text{ms}$ p95 `[TARGET]`
- Online `run_scenario` shock propagation: $< 200\text{ms}$ p95 `[TARGET]`
- Morning Briefing generation: $< 3\text{s}$ p95 `[TARGET]`
- Forecast execution (28-day horizon `[ASSUMPTION]`): $< 500\text{ms}$ p95 `[TARGET]`  
**Constraints**:
- Constitution Principle I: Zero metric hallucination (Metric Auditor Gate) `[TARGET]`
- Constitution Principle II: No autonomous writes (KMS-signed draft action intents only)
- Constitution Principle III: Causal-evidence gate (placebo refuter $p > 0.05$ required for causal assertions) `[TARGET]`
- Constitution Principle VI: Forecaster $\text{MASE} < 1.0$ `[TARGET]`; driver attribution sum $\equiv 100.0\% \pm 0.001\%$ `[TARGET]`

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (LLMs Never Compute Metrics)**: PASS. All quantitative values arrive deterministically via `MetricEngine` and SCM propagation functions. Audited by `MetricAuditorGate`.
- **Principle II (No Autonomous Write-Back)**: PASS. Synthesis recommendations compose proposed `ActionIntentToken` instances; zero direct state mutation sinks.
- **Principle III (Honest Uncertainty & Causal Gate)**: PASS. Unverified or failing edges trigger the mandatory refusal: `"correlation detected; insufficient evidence for causation."` Planted placebo edges are rejected ($p \le 0.05$ `[TARGET]`).
- **Principle IV (Ontology-Only Access)**: PASS. Synthesis consumes domain entities and metrics strictly through OMCP tool contracts (`contracts/omcp-tools.json`).
- **Principle V (Provenance & Labelling)**: PASS. Every figure carries provenance labels (`[BRIEF]`, `[ASSUMPTION]`, `[ILLUSTRATIVE]`, `[TARGET]`, `[SPIKE]`) and cites entity ID, metric version, and `as_of` timestamp.
- **Principle VI (Eval-First & Baselines)**: PASS. Forecaster committed to beat seasonal-naive $y_{t-28}$ baseline ($\text{MASE} < 1.0$ `[TARGET]`); driver attribution committed to beat equal-split baseline and sum to $100.0\% \pm 0.001\%$ `[TARGET]`.
- **Principle VII (Decoupled Pipelines)**: PASS. Structural equations fitted and refuted offline (nightly, cached per Spike S-04 / ADR-005 `[SPIKE]`); online turn performs sub-second parametric shock propagation only.
- **Principle VIII (Deterministic Fallback)**: PASS. Briefing and synthesis provide cached replay fallbacks tagged with `[REPLAY]` badges during upstream outages.

---

## Mathematical Formulations & Algorithms

### 1. Structural Causal Equations & DoWhy-Style Refuters (ADR-005)
For each directed edge $X \rightarrow Y$ in the Causal DAG:
- **Structural Estimation**: Ridge Regression with $L_2$ penalty $\alpha = 1.0$ `[ASSUMPTION]`:
  $$\hat{\beta} = (X^T X + \alpha I)^{-1} X^T Y$$
- **Placebo-Treatment Refuter**: Permute treatment $X \rightarrow X_{\text{perm}}$, refit $\hat{\beta}_{\text{placebo}}$, calculate $p$-value via two-sided Student's $t$-test.
  $$\text{Pass Condition}: p > 0.05 \quad \text{(effect indistinguishable from zero)} \quad [TARGET]$$
- **Random Common Cause Refuter**: Introduce synthetic random confounder $Z \sim \mathcal{N}(0, 1)$, refit $\hat{\beta}_{\text{confounder}}$.
  $$\text{Pass Condition}: \left| \frac{\hat{\beta}_{\text{confounder}} - \hat{\beta}}{\hat{\beta}} \right| \le 0.20 \quad [TARGET]$$
- **Data Subset Stability Refuter**: Fit across $K = 50$ random $80\%$ sub-samples.
  $$\text{Pass Condition}: \text{std}(\hat{\beta}_{\text{subset}}) / |\hat{\beta}| \le 0.20 \quad [TARGET]$$

### 2. Forecaster & 100% Additive Attribution Decomposition
- **Autoregressive Feature Vector**: $[y_{t-1}, y_{t-7}, y_{t-14}, y_{t-28}]$ augmented with upstream SCM leading indicators $[X_{\text{lead}, 1}, X_{\text{lead}, 2}]$.
- **Driver Attribution Summation**:
  Given forecast variance $\Delta Y$, raw contributions $A_k = |\Delta X_k \cdot W_{X_k \rightarrow Y}|$.
  $$P_k = \frac{A_k}{\sum_{j=1}^K A_j} \times 100.0\%$$
  Apply Hare-Niemeyer largest-remainder rounding ensuring:
  $$\sum_{k=1}^K P_k \equiv 100.0\% \pm 0.001\% \quad [TARGET]$$
  If all $\Delta X_k = 0$, allocate balanced uniform distribution ($100 / K \%$ each).

### 3. Doubly Robust AIPW Offline Recalibration
- **Propensity Score**: Logistic score $e(X) = \sigma(w^T X)$ clipped to $[0.01, 0.99]$ `[ASSUMPTION]`.
- **AIPW Estimator**:
  $$\hat{\tau}_{\text{AIPW}} = \frac{1}{N} \sum_{i=1}^N \left( \hat{\mu}_1(X_i) - \hat{\mu}_0(X_i) + \frac{A_i (Y_i - \hat{\mu}_1(X_i))}{e(X_i)} - \frac{(1 - A_i)(Y_i - \hat{\mu}_0(X_i))}{1 - e(X_i)} \right)$$
  Achieves $\ge 50\%$ lower bias `[TARGET]` than unweighted observational means under confounded action selection.

---

## Project Structure

### Documentation (this feature)

```text
specs/006-synthesis-engine/
├── spec.md              # Feature specification
├── research.md          # Spike S-04 / ADR-005 resolution and technical foundations
├── data-model.md        # Pydantic v2 entities and schemas
├── contracts/           # JSON schemas for briefing, forecast, scenario
│   ├── synthesis-briefing.schema.json
│   ├── synthesis-forecast.schema.json
│   └── synthesis-scenario.schema.json
├── quickstart.md        # End-to-end developer quickstart
├── plan.md              # This implementation plan
└── checklists/
    └── requirements.md  # Quality and constitution checklist
```

### Source Code (repository layout)

```text
FEIOS/
├── src/eios/
│   ├── synthesis/
│   │   ├── __init__.py           # Exports SynthesisEngine, SCMRunner, Forecaster, ScenarioSimulator
│   │   ├── models.py             # Pydantic v2 domain models
│   │   ├── scm.py                # Causal DAG representation, topological sort, SCMCache
│   │   ├── refutation.py         # Placebo, random common cause, subset stability refuters
│   │   ├── scm_runner.py         # Nightly/batch runner fitting historical data and writing SCMCache
│   │   ├── forecast.py           # Multivariate Ridge forecaster, prediction intervals, MASE
│   │   ├── attribution.py        # Additive driver attribution strictly summing to 100.0%
│   │   ├── scenario.py           # Parametric shock injection, bounds, mitigation ranking
│   │   ├── briefing.py           # Morning briefing generation, ranking, replay fallback
│   │   ├── recommendations.py    # Governed recommendation cards, Action Intent formatting
│   │   └── aipw.py               # Doubly Robust Augmented Inverse Propensity Weighting
│   └── ontology/
│       └── omcp/
│           └── server.py         # Wire synthesis handlers to OMCPServer
├── tests/
│   └── synthesis/
│       ├── test_scm_dag.py
│       ├── test_refutation.py
│       ├── test_scm_runner.py
│       ├── test_forecast_engine.py
│       ├── test_driver_attribution.py
│       ├── test_scenario_simulation.py
│       ├── test_morning_briefing.py
│       ├── test_recommendation_composer.py
│       ├── test_aipw_flywheel.py
│       ├── test_omcp_synthesis_integration.py
│       └── test_e2e_synthesis.py
```

---

## Phased Implementation Roadmap

### Phase 1: Setup & Data Contracts
- Create directory structure under `FEIOS/src/eios/synthesis/` and `FEIOS/tests/synthesis/`.
- Implement `models.py` with Pydantic v2 entities matching `data-model.md`.
- Copy contracts into `FEIOS/schemas/synthesis/`.

### Phase 2: Structural Causal Model (SCM), Refutation & Caching (P1 🎯 MVP)
- Implement `refutation.py`: Placebo treatment refuter ($p > 0.05$ pass `[TARGET]`), random common cause refuter ($\Delta \le 0.20$ `[TARGET]`), data subset stability refuter ($\Delta \le 0.20$ `[TARGET]`).
- Implement `scm.py`: NetworkX directed acyclic graph, linear structural equations, cycle detection, serialization to `SCMCache` (`synthesis_scm_cache.json`).
- Implement `scm_runner.py`: Nightly/batch runner fitting historical data, validating Causal-Evidence Gate, and writing cache manifest.

### Phase 3: Predictive Forecasting & 100% Additive Attribution (P1)
- Implement `forecast.py`: Multivariate Ridge forecaster using autoregressive lags and upstream DAG leading indicators, generating point estimates, empirical 95% prediction intervals, and out-of-sample MASE calculations ($\text{MASE} < 1.0$ `[TARGET]`).
- Implement `attribution.py`: Path-based counterfactual variance decomposition with largest-remainder rounding guaranteeing $\sum \text{pct} \equiv 100.0\% \pm 0.001\%$ `[TARGET]`.

### Phase 4: Parametric Scenario Simulation & Mitigation Ranking (P2)
- Implement `scenario.py`: Parametric shock injection traversing SCM in topological order in $< 200\text{ms}$ p95 `[TARGET]`.
- Compute propagated deltas with 95% confidence bounds and assumption tracking.
- Implement mitigation action ranking matching adverse outcomes to registered Action Types.

### Phase 5: Proactive Morning Briefing & Replay Fallback (P2)
- Implement `briefing.py`: Queries Semantic Metric Layer for 24-hour and 28-day deltas, surfaces $\ge 3$ insights `[BRIEF]`, $\ge 2$ risks `[BRIEF]`, and $\ge 1$ opportunity `[BRIEF]` with drill-down prompts in $< 3\text{s}$ p95 `[TARGET]`.
- Implement deterministic cached replay fallback with `[REPLAY]` metadata tag.

### Phase 6: Governed Recommendations & Doubly Robust AIPW Logging (P3)
- Implement `recommendations.py`: Formats decision cards with impact ranges, pros/cons, confidence ($\ge 0.80$ `[TARGET]`), citations, and draft `ActionIntentToken` proposals.
- Calculate and log proposal propensity score $e(X) \in [0.01, 0.99]$ `[ASSUMPTION]` and causal context vector $X$.
- Implement `aipw.py`: Augmented Inverse Propensity Weighting offline estimator for unbiased causal recalibration on logged decisions ($\ge 50\%$ lower bias `[TARGET]`).

### Phase 7: OMCP Integration & Auditor Gate Verification (P3)
- Update `FEIOS/src/eios/ontology/omcp/server.py` to dispatch all 5 synthesis tools:
  - `get_causal_chain` (in $< 100\text{ms}$ p95 `[TARGET]`)
  - `run_scenario` (in $< 200\text{ms}$ p95 `[TARGET]`)
  - `get_forecast`
  - `get_briefing`
  - `propose_action`
- Verify integration with `MetricAuditorGate` and Red-Line CI gates (RL-1 to RL-7) with zero tolerance `[TARGET]`.

### Phase 8: Polish, Test Coverage & Evaluation Harness Integration
- Write comprehensive unit, property, and end-to-end integration tests in `FEIOS/tests/synthesis/`.
- Register synthesis validation suite in `evals/registry.yaml`.
- Enforce test coverage gate: `uv run pytest tests/synthesis/ --cov=eios.synthesis --cov-fail-under=80` `[TARGET]`.
- Verify clean execution of `ruff check` and `ruff format` (0 errors `[TARGET]`).
