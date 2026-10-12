# Implementation Plan: Evaluation Harness & Anti-Circularity Benchmark Framework (F04)

**Branch**: `005-eval-harness` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-eval-harness/spec.md`

---

## Summary

Feature F04 establishes the **Evaluation Harness & Anti-Circularity Benchmark Framework**, delivering the enterprise operating system's automated verification backbone per `initial_plan.md` §9, `docs/models_and_evals.md`, `docs/synthetic_data_strategy.md`, and Constitution Principle VI (*Eval-First, Baselines, and Anti-Circularity*).

F04 operationalizes:
1. **Red-Line CI Gate Engine (`evals/suites/redlines/`)**: Seven non-negotiable blocking tests (`RL-1` through `RL-7`) enforcing Constitution Principles I (Metric Auditor Gate with statutory citation exemption), II (No autonomous write-back, KMS ECDSA P-256 intent verification), III (Causal gate compliance), IV (Token vault PII scanning), and Security (prompt injection corpus).
2. **Naive Baseline Benchmarking Engine (`evals/suites/baselines/`)**: Pre-registered naive rule-based and statistical baselines for Modules A, B, C, and Synthesis, reporting empirical performance deltas ($\Delta \text{PR-AUC}$, $\Delta \text{F1}$, $\Delta \text{Lead Time}$, $\Delta \text{Queue Reduction}$) on identical data splits.
3. **Multi-Seed Split Runner & Anti-Circularity Isolation (`evals/suites/splits/`)**: Strict separation across `dev`, `validation` ($\ge 10$ seeds with bootstrap confidence intervals), and `sealed holdout` ($\ge 5$ seeds), backed by IAM and process boundaries isolating `eval-truth/` from reasoning agents.
4. **Golden Dialogue & Trajectory Evaluator (`evals/golden/`)**: Multi-turn conversation evaluations checking tool selection accuracy, call ordering, latency budgets, unanswerable query refusals, and Supervisory Router accuracy ($\ge 95\%$).
5. **Reproducible Report Generator & Model Card Exporter (`evals/reports/`)**: Emits byte-deterministic JSON (`eval-report.schema.json`) and rendered GitHub-Flavored Markdown summary tables with complete provenance tags (`[BRIEF]`, `[TARGET]`, `[ILLUSTRATIVE]`, `[ASSUMPTION]`).
6. **Gate Hook Registry Integration (`evals/registry.yaml`)**: Declares all suites across execution tiers (`contract`, `eval_smoke`, `red_line`, `validation`, `sealed`), orchestrated via `python -m evals.cli run --tier <tier>`.

---

## Technical Context

**Language/Version**: Python 3.11+ / 3.14 (platform standard).

**Primary Dependencies**: `pydantic>=2.13.5`, `numpy>=1.26.0`, `scipy>=1.12.0` (for bootstrap distribution sampling and confidence intervals), `scikit-learn>=1.4.0` (for PR-AUC, Brier score, ROC-AUC metrics), `cryptography>=43.0.0` (for RL-7 signature/key validation), `ast` (standard library for static code analysis). Tooling: `pytest` with `pytest-cov`, `ruff`, `mypy`. Rationale and alternatives documented in [research.md](./research.md).

**Storage**: Local filesystem under `evals/reports/` for generated JSON/Markdown artifacts; read-only access to synthetic dataset partitions in hot state (`:memory:eios_hot_state`) and ground truth in `eval-truth/`.

**Testing**: Pytest unit and integration test suite under `tests/evals/`; Red-Line self-tests; coverage gate $\ge 80\%$ line and branch `[TARGET]`.

**Target Platform**: Google Cloud Run container (`linux/amd64` / `linux/arm64`) and developer workstations (macOS/Linux).

**Project Type**: Evaluation harness and CI verification engine (`eios.evals` and `evals/`).

**Performance Goals**:
- `red_line` tier execution time $\le 30\text{s}$ in CI `[TARGET]`.
- `eval_smoke` tier execution time $\le 60\text{s}$ in CI `[TARGET]`.
- Multi-seed bootstrap confidence intervals ($\ge 10$ seeds, $B=1,000$) calculated in $< 3\text{ minutes}$ on standard CPU runners `[TARGET]`.
- Metric calculation latency (PR-AUC, MASE, Brier score) $\le 50\text{ms}$ per 10,000 predictions `[TARGET]`.

**Constraints**:
- Exactly 100% of Red-Line tests pass in CI; zero tolerance for hallucinated numbers, unauthorized mutations, or unrefuted causal assertions (`Principle VI`).
- Zero direct read access granted to agent execution roles on ground truth labels in `eval-truth/` (`Anti-Circularity`, `ADR-015`).
- 100% of reported numbers trace to a seed manifest, git SHA, dataset hash, or brief citation (`Principle V`).

**Scale/Scope**: 7 Red-Line test suites, 4 baseline models, 10 validation seeds, 5 sealed holdout seeds, 10 golden multi-turn dialogues, 5 automated report types.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Principle / Constraint | Pre-research | Post-design |
|---|---|---|---|
| **G1** | **I. LLMs never compute business metrics.** Enforces Red-Line test RL-1; verifies Metric Auditor Gate blocks unanchored figures while exempting statutory citations. | PASS | PASS: Validated in `research.md` §1 and `contracts/redline-test-spec.md`. |
| **G2** | **II. No autonomous write-back.** Enforces Red-Line tests RL-4 and RL-7; verifies static AST write blocking and KMS signed Action Intent Tokens. | PASS | PASS: Validated in `research.md` §1 and `contracts/redline-test-spec.md`. |
| **G3** | **III. Honest uncertainty & Causal Gate.** Enforces Red-Line test RL-3; verifies agent refuses unrefuted causal claims and rejects planted placebo edges ($p > 0.05$). | PASS | PASS: Validated in `research.md` §1 & §2. |
| **G4** | **IV. Data as a product, Ontology access.** Enforces Red-Line test RL-5; verifies zero plaintext PII leaks and validates token vault key consistency. | PASS | PASS: Validated in `research.md` §1. |
| **G5** | **V. Provenance and labelling.** Eval reports enforce inclusion of seed manifest, git SHA, dataset hash, and provenance tags (`[BRIEF]`, `[TARGET]`, etc.). | PASS | PASS: Validated in `contracts/eval-report.schema.json` and `data-model.md` §2. |
| **G6** | **VI. Eval-first, anti-circularity (NON-NEGOTIABLE).** Establishes pre-registered naive baselines, multi-seed split runner, and IAM-isolated ground-truth storage. | PASS | PASS: Validated in `research.md` §2 & §3 and `data-model.md` §2. |
| **G7** | **VII. Specialised agents & decoupled pipelines.** Evaluates Supervisory Router classification accuracy ($\ge 95\%$) and OMCP tool trajectories without redundant loops. | PASS | PASS: Validated in `research.md` §4 and `data-model.md` §2.5. |
| **G8** | **VIII. Deterministic fallback & operability.** Evaluates agent fallback to cached outputs and verifies container cold-boot rehydration SLAs. | PASS | PASS: Validated in `spec.md` edge cases and `quickstart.md` Scenario 4. |
| **G9** | **Secrets & Identity.** Verifies KMS signing, single-use nonces, and approver identity claims in RL-7. | PASS | PASS: Validated in `contracts/redline-test-spec.md`. |
| **G10** | **Validation at boundaries.** All emitted reports validate against `eval-report.schema.json`; suite declarations validate against `evals/registry.yaml` schema. | PASS | PASS: Validated in `contracts/eval-report.schema.json`. |
| **G11** | **Open decisions stay open.** Eval harness evaluates models and agents agnostically without hard-coding specific LLM model IDs or frontend components. | PASS | PASS: Decoupled CLI architecture (`evals.cli`). |
| **G12** | **Red-Line test readiness.** Directly implements and registers all seven Red-Line CI gates (RL-1 to RL-7) in `evals/registry.yaml`. | PASS | PASS: 100% operationalized in `evals/suites/redlines/`. |

Result: 100% PASS on all gates. Complexity Tracking table is not needed.

---

## Project Structure

### Documentation (this feature)

```text
specs/005-eval-harness/
├── spec.md                     # Feature specification (23 FRs, 8 SCs)
├── plan.md                     # This file (/speckit-plan output)
├── research.md                 # Phase 0 architectural & methodology decisions
├── data-model.md               # Phase 1 data entities, schemas, and Model Card layout
├── quickstart.md               # Phase 1 runnable validation scenarios
├── contracts/
│   ├── eval-report.schema.json # JSON Schema for machine-readable eval reports
│   ├── model-card.schema.json  # JSON Schema for standardized model cards
│   └── redline-test-spec.md    # Specifications & gating criteria for RL-1..RL-7
├── checklists/
│   └── requirements.md         # Passed quality checklist
└── tasks.md                    # Created by /speckit-tasks (Phase 2)
```

### Source Code (repository root)

```text
FEIOS/
├── evals/
│   ├── __init__.py
│   ├── cli.py                  # CLI runner: python -m evals.cli run --tier <tier>
│   ├── registry.yaml           # Gate hook registry (contract, eval_smoke, red_line, validation, sealed)
│   ├── suites/
│   │   ├── __init__.py
│   │   ├── redlines/
│   │   │   ├── __init__.py
│   │   │   ├── runner.py       # Red-Line suite aggregator
│   │   │   ├── test_rl1_hallucination.py
│   │   │   ├── test_rl2_citation.py
│   │   │   ├── test_rl3_causal_gate.py
│   │   │   ├── test_rl4_no_autonomous_write.py
│   │   │   ├── test_rl5_pii_leakage.py
│   │   │   ├── test_rl6_prompt_injection.py
│   │   │   └── test_rl7_action_intent.py
│   │   ├── baselines/
│   │   │   ├── __init__.py
│   │   │   ├── module_a_rules.py     # Static threshold rules (Client AML)
│   │   │   ├── module_b_opposite.py  # 1-hop opposite trading match (Partner Fraud)
│   │   │   ├── module_c_recency.py   # Recency threshold rule (Partner Churn)
│   │   │   └── synthesis_naive.py    # Seasonal naive + equal attribution
│   │   └── splits/
│   │       ├── __init__.py
│   │       ├── runner.py             # Multi-seed split runner
│   │       └── bootstrap.py          # 95% bootstrap confidence interval estimator
│   ├── golden/
│   │   ├── __init__.py
│   │   ├── dialogues/                # Multi-turn golden dialogue scenario YAMLs
│   │   └── trajectory_eval.py        # OMCP tool trajectory and router evaluator
│   └── reports/
│       ├── __init__.py
│       ├── generator.py              # JSON & Markdown report generator
│       └── model_cards/              # Exported model cards
├── src/
│   └── eios/
│       └── evals/                    # Core evaluation support library
│           ├── __init__.py
│           ├── metrics.py            # PR-AUC, Brier score, MASE, lift calculations
│           ├── scanner.py            # PII & AST code visitors
│           └── isolation.py          # Ground-truth IAM and process boundary guard
└── tests/
    └── evals/                        # Unit tests for the evaluation harness itself
        ├── conftest.py
        ├── test_bootstrap.py
        ├── test_baselines.py
        ├── test_redlines.py
        ├── test_trajectory_eval.py
        └── test_report_generator.py
```

---

## Phase Breakdown & Delivery Strategy

1. **Phase 1: Setup & Foundational Framework**
   - Initialize package layout in `evals/suites/`, `evals/golden/`, `src/eios/evals/`, and `tests/evals/`.
   - Implement core metric computation utilities (`PR-AUC`, `Brier score`, `MASE`, `Lift`) with vectorized NumPy/Scipy support.
   - Configure shared test fixtures, mock synthetic data loaders, and IAM permission simulators under `tests/evals/conftest.py`.

2. **Phase 2: Red-Line CI Gate Engine (RL-1 to RL-7) 🎯 MVP**
   - Implement AST visitor (`ast.NodeVisitor`) and runtime write blocker denying direct database/API mutation calls in agent modules (RL-4).
   - Implement adversarial prompt hallucination tester using `MetricAuditorGate` and `NumericTokenNormalizer` (RL-1).
   - Implement citation verifier checking entity IDs, metric versions, and data product `as_of` timestamps (RL-2).
   - Implement causal gate validator with planted placebo edge rejection ($p > 0.05$) and standardized refusal enforcement (RL-3).
   - Implement PII regex/NER scanner verifying Layer 1 token vault keys (`tok_usr_*`, `tok_id_cluster_*`) (RL-5).
   - Implement prompt injection benchmark runner across $\ge 50$ adversarial test comms/tickets (RL-6).
   - Implement Action Intent cryptographic ECDSA P-256 signature, expiry, and nonce replay verifier (RL-7).
   - Wire up `red_line` tier in `evals/registry.yaml`, updating gate contract test assertions in `tests/contract/gates/test_registry.py` to reflect the populated registry.

3. **Phase 3: Pre-Registered Naive Baseline Engine**
   - Implement naive baseline models for Module A (Static Threshold Rule), Module B (1-Hop Opposite Trade Match), Module C (Recency Inactivity Threshold), and Synthesis (Seasonal-Naive + Equal Driver Split).
   - Implement comparative benchmarking harness and delta calculation engine ($\Delta \text{PR-AUC}$, $\Delta \text{Lead Time}$, $\Delta \text{Queue Reduction}$, $\Delta \text{FPR}$).
   - Verify pre-registered target commitments against synthetic baseline data.

4. **Phase 4: Multi-Seed Split Runner & Bootstrap CI Engine**
   - Implement `dev` (Seed 42), `validation` (Seeds 101–110), and `sealed` (Seeds 901–905) orchestrators.
   - Implement vectorized NumPy percentile bootstrap confidence interval estimator ($B = 1,000$ iterations) calculating 95% CIs in $< 3\text{ minutes}$.
   - Enforce process and IAM boundary checks verifying reasoning agents have zero read access to `eval-truth/`.

5. **Phase 5: Golden Dialogue & Trajectory Evaluator**
   - Author $\ge 10$ golden multi-turn dialogue scenarios covering drills, assumption challenges, unanswerable queries, and parameter shocks.
   - Implement OMCP tool trajectory evaluator penalizing redundant calls and enforcing correct call ordering.
   - Implement Supervisory Router accuracy scorer gating on $\ge 95\%$ accuracy across golden queries `[TARGET]`.
   - Implement latency timer tracking time-to-first-token ($\le 3\text{s}$) and full turn duration ($\le 20\text{s}$) `[TARGET]`.

6. **Phase 6: Reporting, Model Cards & CLI Integration**
   - Implement JSON report generator validating against `contracts/eval-report.schema.json`.
   - Implement GitHub-Flavored Markdown summary renderer embedding provenance tags (`[BRIEF]`, `[TARGET]`, `[ILLUSTRATIVE]`, `[ASSUMPTION]`).
   - Implement Model Card publisher generating calibration metrics (Brier score, reliability curves) and rollback procedures under `evals/reports/model_cards/`.
   - Wire up all suites into `evals/registry.yaml` across tiers (`eval_smoke`, `validation`, `sealed`).
   - Run complete test suite and assert the $\ge 80\%$ test coverage gate.

