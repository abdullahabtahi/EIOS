# Implementation Plan: Closed-Loop Decision Learning Flywheel (014-flywheel)

**Branch**: `014-flywheel` | **Date**: 2026-10-09 | **Spec**: [specs/014-flywheel/spec.md](spec.md)  
**Input**: Feature specification from `specs/014-flywheel/spec.md`  
**Authoritative References**: `initial_plan.md` §3.1 (L5), §6.1, §12; `docs/engagement_plan.md` §2, §5; `.specify/memory/constitution.md` (Principles I, II, III, V, VI, VII)

---

## Summary

The Closed-Loop Decision Learning Flywheel provides enterprise-grade, counterfactual decision learning across all operational modules (Churn, AML, Partner Fraud, and Executive Synthesis). It solves the operational challenge of **confounding by indication** by capturing proposing agent propensity scores $e(X)$ at proposal time, reconciling 30d/60d/90d actual outcomes against predictions in an immutable ledger, and executing Doubly Robust Augmented Inverse Propensity Weighting (AIPW) to estimate unbiased Average Treatment Effects (ATE). The system subjects all causal claims to the Causal-Evidence Gate (Principle III), recalibrates Structural Causal Model (SCM) DAG edge weights and frontline playbook priors offline (Principle VII), and exports calibration diagnostics (ECE, Brier scores, drift alerts) to the Operations Workstation.

---

## Technical Context

**Language/Version**: Python 3.11+ (running in `FEIOS/` workspace with `uv`)  
**Primary Dependencies**: NumPy, SciPy (`scipy.stats`), Scikit-learn (`LinearRegression`, `LogisticRegression`), Pydantic v2, `jsonschema` (Draft 2020-12), `referencing`  
**Storage**: In-memory / DuckDB embedded tables (`decision_outcomes_ledger`) with immutable cryptographic provenance digests  
**Testing**: `pytest`, `pytest-cov`, `pytest-xdist`  
**Target Platform**: Linux server / macOS local container runtime  
**Project Type**: Python core domain package (`eios.flywheel`) and canonical OMCP tool integration (`eios.ontology.omcp.server`)  
**Performance Goals**:
- Ingest and reconcile 1,000 ledger records in $< 2.0$ seconds.
- Execute Doubly Robust AIPW and refuters on 1,000 samples in $< 1.0$ second.
- Offline SCM DAG edge-weight recalibration in $< 5.0$ seconds.
- OMCP calibration status query in $< 200$ milliseconds.  
**Constraints**: Strict compliance with Constitution Principles I–VIII; zero code/comment leaks settling open decisions `ADR-002`, `ADR-003`, `ADR-009`, `ADR-014`.  
**Scale/Scope**: 5 core user stories, 5 JSON Schema contracts, 6 quickstart validation scenarios, $\ge 80\%$ test coverage.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Requirement | Compliance Analysis | Status |
| :--- | :--- | :--- | :---: |
| **I. LLMs Never Compute Metrics** | All numbers must come from deterministic tools | All AIPW estimates, residuals, ECE, Brier scores, and edge weights are computed via deterministic Python math; LLMs never estimate figures. | **PASS** |
| **II. No Autonomous Write-Back** | No agent-callable execute tool; four-eyes for high severity | Flywheel recalibrates offline model priors and DAG weights; it never executes external mutations or bank transfers. | **PASS** |
| **III. Causal-Evidence Gate** | Confidence interval excludes zero, placebo refuters pass | Implements Placebo Treatment, Random Common Cause, and Data Subset refuters; requires 95% CI to exclude zero before certifying uplift. | **PASS** |
| **IV. Data as Product / OMCP** | Access via governed OMCP, schema enforcement | Exposes calibration diagnostics and reconciliation triggers via canonical OMCP tools with JSON Schema contract validation. | **PASS** |
| **V. Provenance & Labelling** | All claims carry source provenance | Every ledger record and SCM checkpoint contains cryptographic SHA-256 digests, seeds, and execution timestamps. | **PASS** |
| **VI. Eval-First, Baselines** | Tests written before code, $\ge 80\%$ coverage | TDD red-green-refactor workflow; AIPW benchmarked against naive observational baselines on synthetic holdouts; $\ge 80\%$ coverage enforced. | **PASS** |
| **VII. Decoupled Pipelines** | Structural models computed offline; no God Agent | Flywheel execution runs in an offline batch pipeline; interactive turns never fit live models or block on counterfactual estimation. | **PASS** |
| **Open Decisions Protected** | ADR-002, ADR-003, ADR-009, ADR-014 stay open | Technology-agnostic domain interfaces; no specific UI framework or API wire transport assumed. | **PASS** |

---

## Project Structure

### Documentation (this feature)

```text
specs/014-flywheel/
├── spec.md              # Feature specification
├── plan.md              # This implementation plan
├── research.md          # Technical research & architectural decisions (Phase 0)
├── data-model.md        # Domain entities, Pydantic v2 models, state transitions (Phase 1)
├── quickstart.md        # 6 runnable validation scenarios (Phase 1)
├── contracts/           # Draft 2020-12 JSON Schema contracts (Phase 1)
│   ├── decision-outcome-record.schema.json
│   ├── causal-uplift-estimate.schema.json
│   ├── scm-recalibration-checkpoint.schema.json
│   ├── calibration-diagnostics-report.schema.json
│   └── playbook-policy-prior.schema.json
├── checklists/          # Quality validation checklists
│   └── requirements.md
└── tasks.md             # Implementation tasks (Phase 2, via /speckit-tasks)
```

### Source Code Layout

```text
FEIOS/
├── src/
│   └── eios/
│       ├── flywheel/
│       │   ├── __init__.py           # Package exports and version
│       │   ├── schemas.py            # JSON Schema registry and Draft 2020-12 validators
│       │   ├── models.py             # Pydantic v2 domain schemas (DecisionOutcomeRecord, etc.)
│       │   ├── ledger.py             # Multi-horizon DecisionOutcomesLedger storage & reconciliation
│       │   ├── aipw.py              # Doubly Robust AIPW Causal Estimator
│       │   ├── refuters.py           # Causal-Evidence Gate refuter test suite (Principle III)
│       │   ├── recalibration.py      # Offline SCM DAG edge-weight and playbook prior updater
│       │   └── diagnostics.py        # Expected Calibration Error (ECE) and Brier score engine
│       └── ontology/
│           └── omcp/
│               └── server.py         # Wire canonical OMCP tools: get_flywheel_calibration_status
└── tests/
    └── flywheel/
        ├── __init__.py
        ├── test_outcomes_ledger.py
        ├── test_aipw_estimator.py
        ├── test_causal_gate_refuters.py
        ├── test_scm_dag_recalibration.py
        ├── test_playbook_priors.py
        ├── test_calibration_diagnostics.py
        └── test_contracts_validation.py
```

---

## Complexity Tracking

> *No constitutional violations or unjustified complexity detected.*

| Principle / Gate | Deviation | Justification |
| :--- | :--- | :--- |
| *None* | *None* | Pure Python implementation satisfying Principles I–VIII. |
