"""Baseline runner and report (US4): pre-registered thresholds, a spend cap, honest reports, comparison."""

from pathlib import Path

import pytest

from eios.agent_gates.report import build_report, compare_reports, latency_summary, render_markdown
from evals.agent.baseline import (
    SpendCapError,
    ThresholdsError,
    check_spend_cap,
    load_thresholds,
    select_cases,
)


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


def _turn(
    latency: float, outcome: str = "completed", reason: str | None = None
) -> dict[str, object]:
    return {"outcome": outcome, "latency_ms": latency, "inconclusive_reason": reason}


def test_p95_over_every_turn_counts_timeouts_at_the_time_they_took() -> None:
    turns = [_turn(1000.0 + i) for i in range(18)]
    turns += [_turn(30000.0, "inconclusive", "deadline of 30.0s exceeded")] * 2
    summary = latency_summary(turns)
    assert summary["turns"] == 20
    assert summary["timed_out"] == 2
    assert summary["p95_ms"] == 30000.0


def test_a_capability_gap_is_not_a_slow_turn() -> None:
    turns = [_turn(1000.0), _turn(0.0, "inconclusive", "capability_missing: knowledge.regulation")]
    summary = latency_summary(turns)
    assert summary["turns"] == 1
    assert summary["timed_out"] == 0


def test_no_turns_means_not_measured() -> None:
    assert latency_summary([])["p95_ms"] is None


def test_only_selects_golden_scenarios_and_attacks_by_id_and_refuses_an_unknown_id() -> None:
    from pathlib import Path

    from eios.agent_gates.cases import load_attack_cases, load_golden_cases

    root = Path(__file__).resolve().parents[2] / "evals" / "golden"
    golden, attacks = load_golden_cases(root / "agent_cases"), load_attack_cases(root / "attacks")
    some_golden, some_attack = golden[0].scenario_id, attacks[0].case_id
    picked_g, picked_a = select_cases(golden, attacks, [some_golden, some_attack])
    assert [c.scenario_id for c in picked_g] == [some_golden]
    assert [a.case_id for a in picked_a] == [some_attack]
    assert select_cases(golden, attacks, None) == (golden, attacks)
    with pytest.raises(ValueError, match="no_such_case"):
        select_cases(golden, attacks, ["no_such_case"])
