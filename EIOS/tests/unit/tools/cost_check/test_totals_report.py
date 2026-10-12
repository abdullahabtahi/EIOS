"""Acceptance scenario 4: totals over verified rows only; every figure shows its provenance."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from tests.support import cost_repo
from tests.support.clock import FixedClock
from tools.cost_check.__main__ import main
from tools.cost_check.repo import check_repo
from tools.cost_check.totals import Totals

TODAY = FixedClock().now().date()
_PLAIN_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _totals(tmp_path: Path, csv: str | None = None) -> Totals:
    repo = cost_repo.materialise(tmp_path / "repo", csv=csv)
    result = check_repo(repo, TODAY)
    assert result.totals is not None
    return result.totals


def test_totals_are_computed_over_verified_rows_only(tmp_path: Path) -> None:
    totals = _totals(tmp_path)
    assert {line.driver for line in totals.verified} == {
        "model tokens input",
        "model tokens output",
        "compute",
    }
    # 500 x 1.0 + 200 x 2.0 + 100 x 0.5, computed by the tool
    assert totals.total == Decimal("950")


def test_a_row_with_a_blank_price_or_quantity_is_reported_unverified_and_excluded(
    tmp_path: Path,
) -> None:
    totals = _totals(tmp_path)
    reasons = {line.driver: line.reason for line in totals.unverified}
    assert set(reasons) == {"object storage", "scanning", "key management"}
    assert "unit_price" in reasons["object storage"]
    assert "quantity" in reasons["key management"]
    assert not {line.driver for line in totals.verified} & set(reasons)


def test_with_nothing_verified_there_is_no_total(tmp_path: Path) -> None:
    totals = _totals(tmp_path, csv="blank_price")
    assert totals.verified == ()
    assert totals.total is None
    assert len(totals.unverified) == 3


def test_each_verified_line_carries_source_pricing_date_and_tag(tmp_path: Path) -> None:
    totals = _totals(tmp_path)
    by_driver = {line.driver: line for line in totals.verified}
    compute = by_driver["compute"]
    assert compute.source == "fixture price sheet"
    assert compute.verified_on == date(2025, 12, 20)
    assert compute.tag == "[ILLUSTRATIVE]"
    assert compute.line_total == Decimal("50")
    assert by_driver["model tokens input"].tag == "[SPIKE]"


def _run(repo: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = main(["--repo-root", str(repo)], clock=FixedClock())
    return code, capsys.readouterr().out


def test_the_printed_report_shows_source_date_and_tag_for_every_figure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _run(cost_repo.materialise(tmp_path / "repo"), capsys)
    assert code == 0
    for driver, source, verified_on, tag in [
        ("model tokens input", "fixture price sheet (spike S-01)", "2025-12-15", "[SPIKE]"),
        ("compute", "fixture price sheet", "2025-12-20", "[ILLUSTRATIVE]"),
    ]:
        (line,) = [ln for ln in out.splitlines() if driver in ln and "=" in ln]
        assert source in line
        assert verified_on in line
        assert tag in line
    assert "unverified" in out
    assert "950" in out


def _leaves(node: object) -> Iterator[object]:
    if isinstance(node, dict):
        for value in node.values():
            yield from _leaves(value)
    elif isinstance(node, list):
        for value in node:
            yield from _leaves(value)
    else:
        yield node


def test_the_report_holds_no_figure_that_is_not_derived_from_a_row(tmp_path: Path) -> None:
    repo = cost_repo.materialise(tmp_path / "repo")
    assert main(["--repo-root", str(repo)], clock=FixedClock()) == 0
    report = json.loads((repo / "evals" / "reports" / "cost_check.json").read_text())
    derived = {
        Decimal(v)
        for v in (
            "500", "1.0", "200", "2.0", "100", "0.5", "10", "0.25",  # quantities and prices
            "500.0", "400.0", "50.0", "950.0",  # line totals and the total
        )
    }  # fmt: skip
    figures = {
        Decimal(leaf)
        for leaf in _leaves(report["totals"])
        if isinstance(leaf, str) and _PLAIN_NUMBER.fullmatch(leaf)
    }
    assert figures, "the report must carry figures"
    assert figures <= derived, f"figures not derived from a row: {figures - derived}"
    assert not [leaf for leaf in _leaves(report["totals"]) if isinstance(leaf, float)]


def test_the_report_is_written_to_evals_reports(tmp_path: Path) -> None:
    repo = cost_repo.materialise(tmp_path / "repo", linkage="short_threshold")
    assert main(["--repo-root", str(repo)], clock=FixedClock()) == 0
    report = json.loads((repo / "evals" / "reports" / "cost_check.json").read_text())
    assert report["tool"] == "cost_check"
    assert report["finding_count"] == 0
    assert {w["rule_id"] for w in report["warnings"]} == {"cost.price.stale"}
    assert report["totals"]["verified"], "verified lines are listed"
    assert report["totals"]["unverified"], "unverified lines are listed"


def test_exit_code_zero_on_pass_and_warning_only(tmp_path: Path) -> None:
    assert (
        main(["--repo-root", str(cost_repo.materialise(tmp_path / "a"))], clock=FixedClock()) == 0
    )
    stale = cost_repo.materialise(tmp_path / "b", csv="stale_price")
    assert main(["--repo-root", str(stale)], clock=FixedClock()) == 0


def test_exit_code_one_on_findings(tmp_path: Path) -> None:
    repo = cost_repo.materialise(tmp_path / "repo", csv="price_without_source")
    assert main(["--repo-root", str(repo)], clock=FixedClock()) == 1


def test_exit_code_two_on_a_config_error(tmp_path: Path) -> None:
    repo = cost_repo.materialise(tmp_path / "repo", linkage="unknown_key")
    assert main(["--repo-root", str(repo)], clock=FixedClock()) == 2
    assert main(["--repo-root", str(tmp_path / "does-not-exist")], clock=FixedClock()) == 2
    assert main(["--bogus"], clock=FixedClock()) == 2


def test_exit_code_two_when_the_cost_model_is_missing(tmp_path: Path) -> None:
    repo = cost_repo.materialise(tmp_path / "repo")
    (repo / cost_repo.CSV_TARGET).unlink()
    assert main(["--repo-root", str(repo)], clock=FixedClock()) == 2
