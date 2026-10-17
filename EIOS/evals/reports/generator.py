"""Evaluation Report Generator & Schema Validator (T055).

Builds EvalReport instances, validates serialized JSON against schemas/evals/eval-report.schema.json,
and renders GitHub-Flavored Markdown tables with provenance tags ([TARGET], [BRIEF], [ASSUMPTION]).
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jsonschema

from eios.evals.models import (
    BaselineComparison,
    EvalReport,
    MetricConfidenceInterval,
    RedLineID,
    RedLineResult,
    SeedManifest,
    Tier,
)


def get_schema_path() -> Path:
    # First check relative to repo root
    cand1 = Path("schemas/evals/eval-report.schema.json")
    if cand1.is_file():
        return cand1
    cand2 = Path("FEIOS/schemas/evals/eval-report.schema.json")
    if cand2.is_file():
        return cand2
    return Path(__file__).resolve().parents[2] / "schemas" / "evals" / "eval-report.schema.json"


def validate_report_json(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a serialized evaluation report dictionary against JSON Schema."""
    schema_path = get_schema_path()
    with open(schema_path, encoding="utf-8") as f:
        schema = json.load(f)

    validator = jsonschema.Draft202012Validator(schema)
    errors = [e.message for e in validator.iter_errors(data)]
    return len(errors) == 0, errors


def build_sample_eval_report() -> EvalReport:
    """Build a comprehensive sample EvalReport conforming to schema."""
    git_sha = "0123456789abcdef0123456789abcdef01234567"
    manifest = SeedManifest(
        tier=Tier.VALIDATION,
        seeds=[101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        git_sha=git_sha,
        dataset_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        spec_version="1.0.0",
        generated_at=datetime.now(UTC),
    )

    red_line_results = [
        RedLineResult(
            test_id=RedLineID.RL_1,
            name="Metric Hallucination Gate",
            passed=True,
            total_evaluated=50,
            tolerance=0,
        ),
        RedLineResult(
            test_id=RedLineID.RL_2,
            name="Citation & Provenance Coverage",
            passed=True,
            total_evaluated=25,
            tolerance=0,
        ),
        RedLineResult(
            test_id=RedLineID.RL_3,
            name="Causal Gate Compliance",
            passed=True,
            total_evaluated=10,
            tolerance=0,
        ),
        RedLineResult(
            test_id=RedLineID.RL_4,
            name="No Autonomous Write-Back",
            passed=True,
            total_evaluated=30,
            tolerance=0,
        ),
        RedLineResult(
            test_id=RedLineID.RL_5,
            name="PII Leakage Scanner",
            passed=True,
            total_evaluated=40,
            tolerance=0,
        ),
        RedLineResult(
            test_id=RedLineID.RL_6,
            name="Prompt Injection Corpus",
            passed=True,
            total_evaluated=52,
            tolerance=0,
        ),
        RedLineResult(
            test_id=RedLineID.RL_7,
            name="Governed Action Intent Verification",
            passed=True,
            total_evaluated=15,
            tolerance=0,
        ),
    ]

    baseline_comparisons = [
        BaselineComparison(
            module="Module A",
            metric_name="PR-AUC",
            baseline_method="Static Threshold Rules (deposit > X, velocity > Y)",
            candidate_model="LightGBM Alert Scorer with Graph Features",
            baseline_value=0.62,
            candidate_value=0.94,
            absolute_delta=0.32,
            relative_lift_pct=51.61,
            pre_registered_target="Recall at fixed alert volume; FPR relative reduction >= 30% [TARGET]",
            target_met=True,
            confidence_interval=MetricConfidenceInterval(lower=0.91, median=0.94, upper=0.96),
        ),
        BaselineComparison(
            module="Module B",
            metric_name="F1 Score",
            baseline_method="Naive Opposite Direction Matcher within 10s",
            candidate_model="Temporal Anti-Correlation & Direction Anti-Correlation Ring Detector",
            baseline_value=0.55,
            candidate_value=0.88,
            absolute_delta=0.33,
            relative_lift_pct=60.0,
            pre_registered_target="Precision/recall on planted pairs; FPR on hedgers >= 20% lift [TARGET]",
            target_met=True,
            confidence_interval=MetricConfidenceInterval(lower=0.85, median=0.88, upper=0.90),
        ),
        BaselineComparison(
            module="Module C",
            metric_name="PR-AUC",
            baseline_method="Inactivity Rule (No login for 14 days)",
            candidate_model="Discrete-Time Hazard Model (Cox PH / Logistic)",
            baseline_value=0.65,
            candidate_value=0.82,
            absolute_delta=0.17,
            relative_lift_pct=26.15,
            pre_registered_target="PR-AUC >= baseline + 0.10, median lead time >= baseline + 7 days [TARGET]",
            target_met=True,
            confidence_interval=MetricConfidenceInterval(lower=0.80, median=0.82, upper=0.84),
        ),
        BaselineComparison(
            module="Synthesis",
            metric_name="MASE",
            baseline_method="Seasonal-Naive (y_{t-28}) + Equal Split Driver Attribution",
            candidate_model="Counterfactual SCM Forecast & Attribution Engine",
            baseline_value=1.0,
            candidate_value=0.25,
            absolute_delta=-0.75,
            relative_lift_pct=-75.0,
            pre_registered_target="MASE < 1.0 on holdout; attribution decomposition sum = 100.0% [TARGET]",
            target_met=True,
            confidence_interval=MetricConfidenceInterval(lower=0.22, median=0.25, upper=0.28),
        ),
    ]

    return EvalReport(
        suite_id="validation-benchmarks",
        timestamp=datetime.now(UTC),
        git_sha=git_sha,
        tier=Tier.VALIDATION,
        passed=True,
        summary="All 7 Red-Line gates passed cleanly with 0 violations. Naive baseline commitments met across Modules A, B, C, and Synthesis. [TARGET] [BRIEF]",
        seed_manifest=manifest,
        red_line_results=red_line_results,
        baseline_comparisons=baseline_comparisons,
        dialogue_eval_results=[],
        latency_metrics={"p50_total_ms": 120.0, "p95_total_ms": 350.0, "max_total_ms": 600.0},
        hardware_and_cost={
            "peak_memory_mb": 256.0,
            "cpu_seconds": 1.25,
            "total_tokens": 1500,
            "estimated_cost_usd": 0.003,
        },
    )


def render_markdown_summary_table(report: EvalReport) -> str:
    """Render a GitHub-Flavored Markdown summary report with provenance tags."""
    pass_str = "PASSED" if report.passed else "FAILED"
    gate_pass_pct = (
        (sum(1 for r in report.red_line_results if r.passed) / len(report.red_line_results) * 100.0)
        if report.red_line_results
        else 100.0
    )

    lines: list[str] = [
        f"# Evaluation Report: `{report.suite_id}`",
        "",
        f"**Tier**: `{report.tier.value}` | **Status**: **{pass_str}** | **Git SHA**: `{report.git_sha[:8]}` | **Timestamp**: {report.timestamp.isoformat()} [BRIEF]",
        "",
        "## Executive Summary",
        f"{report.summary}",
        "",
        "## Overall Gating Status",
        "| Suite ID | Tier | Status | Gate Pass % |",
        "|---|---|---|---|",
        f"| `{report.suite_id}` | `{report.tier.value}` | `{pass_str}` | {gate_pass_pct:.1f}% |",
        "",
        "## Red-Line Gates (RL-1 to RL-7) `[TARGET]`",
        "| Gate ID | Name | Evaluated | Violations | Tolerance | Status |",
        "|---|---|---|---|---|---|",
    ]

    for rl in report.red_line_results:
        st = "PASS" if rl.passed else "FAIL"
        lines.append(
            f"| `{rl.test_id}` | {rl.name} | {rl.total_evaluated} | {rl.violations_detected} | {rl.tolerance} | **{st}** |"
        )

    lines.extend(
        [
            "",
            "## Naive Baselines vs Candidate Models `[TARGET]`",
            "| Module | Metric | Baseline Method | Baseline | Candidate Model | Candidate | Delta | Lift (%) | 95% Bootstrap CI | Target Met |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )

    for comp in report.baseline_comparisons:
        ci_str = (
            f"[{comp.confidence_interval.lower:.2f}, {comp.confidence_interval.upper:.2f}]"
            if comp.confidence_interval
            else "N/A"
        )
        tm_str = "YES" if comp.target_met else "NO"
        lines.append(
            f"| {comp.module} | `{comp.metric_name}` | {comp.baseline_method} | {comp.baseline_value:.2f} | "
            f"{comp.candidate_model} | {comp.candidate_value:.2f} | {comp.absolute_delta:+.2f} | {comp.relative_lift_pct:+.1f}% | "
            f"{ci_str} | **{tm_str}** |"
        )

    return "\n".join(lines) + "\n"
