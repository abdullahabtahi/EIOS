"""Gateway-to-driver linkage: gateway token prices and cost-model rows must not disagree."""

from __future__ import annotations

from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support import cost_repo
from tests.support.clock import FixedClock
from tools.cost_check.__main__ import main
from tools.cost_check.repo import CostResult, check_repo

TODAY = FixedClock().now().date()
DEV = "config/llm_gateway.dev.yaml"


def _check(
    tmp_path: Path,
    *,
    csv: str | None = None,
    gateway: str | None = None,
    linkage: str | None = None,
) -> CostResult:
    repo = cost_repo.materialise(tmp_path / "repo", csv=csv, gateway=gateway, linkage=linkage)
    return check_repo(repo, TODAY)


def test_equal_prices_pass(tmp_path: Path) -> None:
    assert _check(tmp_path).findings == ()


def test_equal_prices_pass_regardless_of_number_spelling(tmp_path: Path) -> None:
    assert _check(tmp_path, gateway="equal_spelling").findings == ()


def test_a_mismatch_fails_and_names_both_values_and_files(tmp_path: Path) -> None:
    (finding,) = _check(tmp_path, gateway="mismatched_price").findings
    assert finding.rule_id == "linkage.price_mismatch"
    assert finding.file == DEV
    for expected in ("1.5", "1.0", DEV, "docs/cost_model.csv", "model tokens input"):
        assert expected in finding.message


def test_a_gateway_price_with_no_linked_row_fails(tmp_path: Path) -> None:
    (finding,) = _check(tmp_path, linkage="missing_output_key").findings
    assert finding.rule_id == "linkage.unlinked_price"
    assert finding.file == DEV
    assert "prices.output_per_unit" in finding.message


def test_a_gateway_file_the_linkage_does_not_name_is_not_exempt(tmp_path: Path) -> None:
    findings = _check(tmp_path, linkage="dev_not_named").findings
    assert {f.rule_id for f in findings} == {"linkage.unlinked_price"}
    assert {f.file for f in findings} == {DEV}
    assert len(findings) == 2


def test_a_linked_row_with_no_gateway_price_passes(tmp_path: Path) -> None:
    assert _check(tmp_path, gateway="no_prices").findings == ()


def test_a_stub_price_tagged_illustrative_needs_no_verified_row_price(tmp_path: Path) -> None:
    result = _check(tmp_path, csv="blank_price")
    assert result.findings == ()


def test_a_real_gateway_price_needs_a_verified_row_price(tmp_path: Path) -> None:
    findings = _check(tmp_path, csv="blank_price", gateway="assumed_price").findings
    assert {f.rule_id for f in findings} == {"linkage.price_unverified"}
    assert len(findings) == 2
    assert all(f.file == DEV for f in findings)
    assert "model tokens" in findings[0].message


def test_a_unit_mismatch_fails(tmp_path: Path) -> None:
    findings = _check(tmp_path, gateway="other_unit").findings
    assert {f.rule_id for f in findings} == {"linkage.unit_mismatch"}
    assert "1000000 tokens" in findings[0].message
    assert "1000 tokens" in findings[0].message


@pytest.mark.parametrize(
    ("linkage", "needle"),
    [
        ("unknown_key", "input_per_1k"),
        ("unknown_driver", "model tokens outputs"),
        ("missing_gateway_file", "llm_gateway.nowhere.yaml"),
    ],
)
def test_a_changed_linkage_key_is_a_config_error(tmp_path: Path, linkage: str, needle: str) -> None:
    repo = cost_repo.materialise(tmp_path / "repo", linkage=linkage)
    with pytest.raises(ConfigError, match=needle):
        check_repo(repo, TODAY)
    assert main(["--repo-root", str(repo)], clock=FixedClock()) == 2


@pytest.mark.parametrize("gateway", ["bad_price", "not_a_mapping"])
def test_an_unreadable_gateway_price_is_a_config_error(tmp_path: Path, gateway: str) -> None:
    repo = cost_repo.materialise(tmp_path / "repo", gateway=gateway)
    with pytest.raises(ConfigError, match=r"llm_gateway\.dev\.yaml"):
        check_repo(repo, TODAY)


def test_a_linkage_failure_makes_the_tool_exit_one(tmp_path: Path) -> None:
    repo = cost_repo.materialise(tmp_path / "repo", gateway="mismatched_price")
    assert main(["--repo-root", str(repo)], clock=FixedClock()) == 1
