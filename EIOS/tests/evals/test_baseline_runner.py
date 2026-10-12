"""Tests for Baseline Benchmark Runner & Delta Calculations (T032)."""

from evals.suites.baselines.runner import (
    run_all_baselines,
)


def test_run_all_baselines():
    report = run_all_baselines()
    assert report["all_benchmarks_computed"] is True
    assert len(report["comparisons"]) == 4

    modules = {c["module"] for c in report["comparisons"]}
    assert "Module A" in modules
    assert "Module B" in modules
    assert "Module C" in modules
    assert "Synthesis" in modules

    for comp in report["comparisons"]:
        assert "metric_name" in comp
        assert "baseline_value" in comp
        assert "candidate_value" in comp
        assert "absolute_delta" in comp
        assert "relative_lift_pct" in comp
        assert "pre_registered_target" in comp
        assert "target_met" in comp
