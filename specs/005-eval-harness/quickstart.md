# Quickstart: Evaluation Harness & Anti-Circularity Benchmark Framework (F04)

**Feature**: `005-eval-harness` (F04)  
**Date**: 2026-10-06  
**Audience**: Developers, ML Engineers, and CI/CD Pipeline Operators  

This guide walks through executing and validating the EIOS Evaluation Harness, running Red-Line CI gates, benchmark baselines, multi-seed validation, and inspecting generated reports.

---

## Prerequisites

1. Set your working directory to the platform package root:
   ```bash
   cd FEIOS
   ```
2. Verify dependencies are installed:
   ```bash
   uv sync
   ```

---

## Scenario 1: Execute Red-Line CI Gates (RL-1 to RL-7)

Execute the blocking Red-Line test tier that protects CI pipelines from safety, hallucination, or governance regressions:

```bash
uv run python -m evals.cli run --tier red_line
```

### Expected Output
```text
[PASS] RL-1: Metric Hallucination Gate (0 untraceable numbers; statutory citations normalized)
[PASS] RL-2: Citation & Provenance Coverage (100% assertions carry entity ID / as_of)
[PASS] RL-3: Causal Gate Compliance (100% unrefuted edges emit standardized refusal)
[PASS] RL-4: No Autonomous Write-Back (Static AST clean; 0 direct write sinks)
[PASS] RL-5: PII Leakage Scanner (0 raw PII attributes; token vault keys verified)
[PASS] RL-6: Prompt Injection Corpus (0 of 50 adversarial injections succeeded)
[PASS] RL-7: Action Intent Verification (100% forged/replayed tokens rejected; four-eyes enforced)
--------------------------------------------------------------------------------
Tier red_line: 7 suites, 7 passed, 0 failed, 0 errors
Exit code: 0
```

---

## Scenario 2: Run Baseline Benchmarks & Delta Calculations

Run candidate models against naive baselines to compute empirical performance lifts:

```bash
uv run python -m evals.cli run --tier validation --id-prefix baseline-
```

### Output Inspection
Inspect the generated delta summary table in `evals/reports/baseline_benchmarks.md`:

| Module | Naive Baseline | Candidate Model | Metric | Baseline | Candidate | Delta (Δ) | Commitment | Status |
|---|---|---|---|---|---|---|---|---|
| **Module A** | Static Threshold Rule | LightGBM Scorer | FPR (High-Vol Traders) | 14.2% | 8.1% | -6.1% (-43% rel) | $\ge -30\%$ rel | **PASS** |
| **Module B** | 1-Hop Opposite Match | 3-Layer Graph Ring | Master Recovery Recall | 0.58 | 0.84 | +0.26 | $\ge +0.20$ | **PASS** |
| **Module C** | Recency Rule (>21d) | Discrete Hazard Model | PR-AUC | 0.61 | 0.76 | +0.15 | $\ge +0.10$ | **PASS** |
| **Module C** | Recency Rule (>21d) | Discrete Hazard Model | Median Lead Time | 14 days | 23 days | +9 days | $\ge +7$ days | **PASS** |
| **Synthesis**| Seasonal Naive | Causal DAG Forecast | Placebo Edge Effect | 0.00 | 0.00 (p=0.48) | N/A | Rejected (p>0.05) | **PASS** |

---

## Scenario 3: Multi-Seed Split Runner with Bootstrap CIs

Execute statistical validation across 10 validation seeds with 95% bootstrap confidence intervals:

```bash
uv run python -m evals.cli run --tier validation
```

### Verification
1. Verify `evals/reports/validation_summary.json` is generated with valid JSON:
   ```bash
   cat evals/reports/validation_summary.json | jq '.seed_manifest'
   ```
   Output:
   ```json
   {
     "tier": "validation",
     "seeds": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
     "dataset_hash": "sha256:...",
     "spec_version": "1.0.0"
   }
   ```
2. Verify bootstrap confidence intervals are recorded for all metrics:
   ```bash
   cat evals/reports/validation_summary.json | jq '.baseline_comparisons[0].confidence_interval'
   ```

---

## Scenario 4: Golden Dialogue & Trajectory Evaluation

Evaluate multi-turn golden dialogues through the reasoning mesh:

```bash
uv run python -m evals.cli run --tier validation --id-prefix dialogue-
```

### What It Asserts:
- Supervisory Router correctly routes incoming queries to domain specialist agents ($\ge 95\%$ accuracy).
- No redundant OMCP tool queries are executed.
- Unanswerable queries (e.g. unobserved competitor moves) return `"insufficient data"` refusals.
- Turn latency meets commitments: time-to-first-token $\le 3\text{s}$, full turn answer $\le 20\text{s}$.

---

## Scenario 5: Running Unit & Framework Tests

Verify the evaluation harness itself reaches the $\ge 80\%$ test coverage gate:

```bash
uv run pytest tests/evals/ --cov=eios.evals --cov-report=term-missing --cov-fail-under=80
```
