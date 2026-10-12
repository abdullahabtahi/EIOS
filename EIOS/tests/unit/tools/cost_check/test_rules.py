"""FR-038 checker rules: one fixture per failure row of contracts/cost-model.md."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support import cost_repo
from tests.support.clock import FixedClock
from tools.common.findings import Finding
from tools.cost_check.repo import CostResult, check_repo

TODAY = FixedClock().now().date()
FAULT_LINE = 4  # every failure fixture puts its fault on line 4


def _check(
    tmp_path: Path,
    *,
    csv: str | None = None,
    linkage: str | None = None,
    today: date = TODAY,
) -> CostResult:
    return check_repo(cost_repo.materialise(tmp_path / "repo", csv=csv, linkage=linkage), today)


def _of(findings: tuple[Finding, ...], rule: str) -> list[Finding]:
    return [f for f in findings if f.rule_id == rule]


def test_the_clean_file_passes_without_findings_or_warnings(tmp_path: Path) -> None:
    result = _check(tmp_path)
    assert result.findings == ()
    assert result.warnings == ()


@pytest.mark.parametrize(
    ("fixture", "rule", "driver"),
    [
        ("price_without_source", "cost.price.source_missing", "compute"),
        ("price_without_date", "cost.price.date_missing", "compute"),
        ("missing_tag", "cost.tag.missing", "compute"),
        ("bad_tag", "cost.tag.invalid", "compute"),
        ("spike_without_id", "cost.spike.id_missing", "compute"),
        ("duplicate_driver", "cost.driver.duplicate", "model tokens input"),
        ("negative_quantity", "cost.quantity.invalid", "compute"),
        ("not_a_number", "cost.quantity.invalid", "compute"),
        ("negative_price", "cost.price.invalid", "compute"),
        ("non_iso_date", "cost.date.not_iso", "compute"),
        ("unknown_reconciliation", "cost.reconciliation.invalid", "compute"),
        ("reconciled_empty_ref", "cost.reconciliation.invalid", "compute"),
        ("empty_unit", "cost.unit.missing", "compute"),
    ],
)
def test_each_failure_row_fails_with_file_line_and_driver(
    tmp_path: Path, fixture: str, rule: str, driver: str
) -> None:
    result = _check(tmp_path, csv=fixture)
    found = _of(result.findings, rule)
    assert len(found) == 1, f"{fixture}: expected one {rule}, got {result.findings}"
    assert found[0].file == "docs/cost_model.csv"
    assert found[0].line == FAULT_LINE
    assert driver in found[0].message
    assert {f.rule_id for f in result.findings} == {rule}, "only the intended rule may fire"


def test_a_driver_named_total_or_subtotal_in_any_case_is_rejected(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="driver_total")
    found = _of(result.findings, "cost.driver.total_name")
    assert [f.line for f in found] == [4, 5]
    assert "Total" in found[0].message
    assert "SubTotal" in found[1].message


def test_a_blank_price_is_allowed(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="blank_price")
    assert result.findings == ()


def test_an_omitted_reconciliation_column_defaults_to_pending(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="no_reconciliation_column")
    assert result.findings == ()


def test_a_stale_price_date_is_a_warning_and_never_a_failure(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="stale_price")
    assert result.findings == ()
    (warning,) = result.warnings
    assert warning.rule_id == "cost.price.stale"
    assert warning.line == FAULT_LINE
    assert "compute" in warning.message
    assert "2025-01-01" in warning.message


def test_the_staleness_threshold_comes_from_configuration(tmp_path: Path) -> None:
    long_threshold = _check(tmp_path / "a", csv="stale_price", linkage="long_threshold")
    assert long_threshold.warnings == ()
    short_threshold = _check(tmp_path / "b", linkage="short_threshold")
    assert short_threshold.findings == ()
    assert {w.rule_id for w in short_threshold.warnings} == {"cost.price.stale"}


def test_staleness_follows_the_injected_date_not_the_system_clock(tmp_path: Path) -> None:
    far_future = datetime(2030, 1, 1, tzinfo=UTC).date()
    result = _check(tmp_path, today=far_future)
    assert result.findings == ()
    assert result.warnings, "prices verified in 2025 are stale by 2030"


def test_a_missing_required_column_is_a_finding(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="missing_column")
    found = _of(result.findings, "cost.header.missing_column")
    assert len(found) == 1
    assert "price_verified_on" in found[0].message
    assert found[0].line == 1


def test_a_short_row_is_a_finding(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="short_row")
    assert [f.rule_id for f in result.findings] == ["cost.row.shape"]


def test_an_empty_file_is_a_finding(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="empty")
    assert {f.rule_id for f in result.findings} == {"cost.header.missing_column"}


def test_a_missing_cost_model_is_a_config_error(tmp_path: Path) -> None:
    repo = cost_repo.materialise(tmp_path / "repo")
    (repo / cost_repo.CSV_TARGET).unlink()
    with pytest.raises(ConfigError, match=r"cost_model\.csv"):
        check_repo(repo, TODAY)


@pytest.mark.parametrize("linkage", ["zero_threshold", "untagged_threshold", "not_a_mapping"])
def test_an_invalid_threshold_configuration_is_a_config_error(tmp_path: Path, linkage: str) -> None:
    repo = cost_repo.materialise(tmp_path / "repo", linkage=linkage)
    with pytest.raises(ConfigError, match=r"cost_linkage\.yaml"):
        check_repo(repo, TODAY)
