"""Baseline runner and report (US4): pre-registered thresholds, a spend cap, honest reports, comparison."""

from pathlib import Path

import pytest

from eios.agent_gates.report import build_report, compare_reports, render_markdown
from evals.agent.baseline import SpendCapError, ThresholdsError, check_spend_cap, load_thresholds


def _result(
    case: str, ok: bool, workstation: str = "aml_investigator", **extra: object
) -> dict[str, object]:
    base: dict[str, object] = {
        "case_id": case,
        "workstation": workstation,
        "suite": "faithfulness",
        "verdict": "pass" if ok else "fail",
        "evidence": "" if ok else f"{case}: figure 16 is the multiplier, not the risk score",
        "latency_ms": 100.0,
        "data_origin": "fixture",
        "identity_source": "request_body",
        "figures_supported": 2 if ok else 1,
        "figures_total": 2,
    }
    return base | extra


def test_a_failing_case_is_listed_with_its_evidence() -> None:
    report = build_report("copilot", [_result("a", True), _result("b", False)], {"git_sha": "abc"})
    md = render_markdown(report)
    assert "b: figure 16 is the multiplier" in md
    assert report["gate"]["proven"] is False


def test_inconclusive_cases_are_listed_separately_and_the_gate_is_not_proven() -> None:
    report = build_report(
        "copilot", [_result("a", True), _result("c", False, verdict="inconclusive")], {}
    )
    assert report["counts"]["inconclusive"] == 1 and report["gate"]["proven"] is False


def test_only_measured_values_appear() -> None:
    report = build_report("copilot", [_result("a", True, latency_ms=None)], {})
    assert report["p95_latency_ms"] is None and report["cost_usd_per_turn"] is None
    assert "None" not in render_markdown(report)


def test_shares_of_fixture_and_request_body_identity_are_reported() -> None:
    report = build_report("copilot", [_result("a", True), _result("b", True)], {})
    assert report["share_fixture"] == 1.0 and report["share_request_body_identity"] == 1.0


def test_comparison_shows_improved_regressed_and_unchanged_cases() -> None:
    before = build_report(
        "copilot", [_result("a", False), _result("b", True), _result("c", True)], {}
    )
    after = build_report("adk", [_result("a", True), _result("b", False), _result("c", True)], {})
    diff = compare_reports(before, after)
    assert diff["improved"] == ["a"] and diff["regressed"] == ["b"] and diff["unchanged"] == ["c"]


def test_thresholds_must_exist_and_be_committed(tmp_path: Path) -> None:
    with pytest.raises(ThresholdsError, match="missing"):
        load_thresholds(tmp_path / "nope.yaml")
    path = tmp_path / "thresholds.yaml"
    path.write_text("faithfulness: 1.0\n", encoding="utf-8")
    assert load_thresholds(path, require_committed=False)["faithfulness"] == 1.0


def test_a_live_run_over_the_spend_cap_stops_before_it_starts() -> None:
    with pytest.raises(SpendCapError):
        check_spend_cap(turns=100, repeats=3, live=True, cap_turns=50)
    check_spend_cap(turns=100, repeats=3, live=False, cap_turns=50)
    check_spend_cap(turns=10, repeats=3, live=True, cap_turns=50)
