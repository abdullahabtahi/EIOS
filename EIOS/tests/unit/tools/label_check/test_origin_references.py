from __future__ import annotations

from collections.abc import Callable

from tools.common.findings import Finding

Scan = Callable[[str], tuple[Finding, ...]]


def test_complete_generator_origin_passes(scan: Scan) -> None:
    text = "Sample is 500 clients generator-run: seed=7 revision=abc1234 dataset=ds-9f.\n"
    assert scan(text) == ()


def test_generator_origin_missing_parts_is_flagged(scan: Scan) -> None:
    (finding,) = scan("Sample is 500 clients generator-run: seed=7 revision=abc1234.\n")
    assert finding.rule_id == "label.origin-incomplete"
    assert "dataset" in finding.message


def test_eval_origin_under_reports_passes(scan: Scan) -> None:
    assert scan("Accuracy is 91 percent eval-report: evals/reports/model.json.\n") == ()


def test_eval_origin_outside_reports_is_flagged(scan: Scan) -> None:
    (finding,) = scan("Accuracy is 91 percent eval-report: docs/model.json.\n")
    assert finding.rule_id == "label.origin-path"


def test_eval_origin_path_traversal_is_flagged(scan: Scan) -> None:
    (finding,) = scan("Accuracy is 91 percent eval-report: evals/reports/../../x.json.\n")
    assert finding.rule_id == "label.origin-path"
