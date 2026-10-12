"""T025: config/gates.yaml is the single definition of every blocking gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from eios.common.errors import ConfigError
from tests.support.repo_builder import build_repo
from tools.gates.gate_config import GateSpec, load_gates, select_gates

REPO = Path(__file__).resolve().parents[4]
CONFIG = REPO / "config" / "gates.yaml"
FR_004_GATES = [
    "lint",
    "types",
    "coverage",
    "contract",
    "eval_smoke",
    "red_line",
    "vuln_scan",
    "secret_scan",
    "iac_plan",
]
STAGES = {"pr", "merge", "promote", "release_candidate"}


def _rows() -> list[dict[str, Any]]:
    document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    rows = document["gates"]
    assert isinstance(rows, list)
    return rows


def test_every_gate_is_blocking_in_f00() -> None:
    assert all(row["blocking"] is True for row in _rows())


def test_gate_ids_are_unique() -> None:
    ids = [row["id"] for row in _rows()]
    assert len(ids) == len(set(ids))


def test_stage_is_one_of_the_four_stages() -> None:
    assert {row["stage"] for row in _rows()} <= STAGES


def test_every_gate_has_a_proof_fixture_that_exists() -> None:
    for row in _rows():
        fixture = REPO / row["proof_fixture"]
        assert fixture.is_dir(), f"{row['id']}: missing proof fixture {row['proof_fixture']}"


def test_proof_fixtures_live_under_faulty_changes() -> None:
    for row in _rows():
        assert row["proof_fixture"] == f"tests/fixtures/faulty_changes/{row['id']}"


def test_the_nine_fr_004_gates_are_present_in_order_at_the_front() -> None:
    ids = [row["id"] for row in _rows()]
    assert ids[: len(FR_004_GATES)] == FR_004_GATES


def test_coverage_threshold_is_eighty() -> None:
    (coverage,) = [row for row in _rows() if row["id"] == "coverage"]
    assert coverage["threshold"] == 80
    assert any("{threshold}" in token for token in coverage["command"])
    text = CONFIG.read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if "threshold: 80" in ln)
    assert "[TARGET]" in line


def test_every_command_is_a_non_empty_list_of_strings() -> None:
    for row in _rows():
        assert row["command"], row["id"]
        assert all(isinstance(c, str) and c.strip() for c in row["command"])


def test_the_loader_accepts_the_real_config_and_keeps_order() -> None:
    gates = load_gates(CONFIG)
    assert [g.id for g in gates][: len(FR_004_GATES)] == FR_004_GATES
    assert all(isinstance(g, GateSpec) for g in gates)
    (coverage,) = [g for g in gates if g.id == "coverage"]
    assert coverage.threshold == 80
    assert isinstance(coverage.command, tuple)


def test_select_gates_filters_by_stage_in_config_order() -> None:
    gates = load_gates(CONFIG)
    pr = select_gates(gates, "pr")
    assert [g.id for g in pr] == [g.id for g in gates if g.stage == "pr"]
    assert select_gates(gates, "merge") == tuple(g for g in gates if g.stage == "merge")


def _config(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    text = yaml.safe_dump({"gates": rows})
    return build_repo(tmp_path, {"config/gates.yaml": text}) / "config" / "gates.yaml"


def _row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": "demo",
        "blocking": True,
        "stage": "pr",
        "proof_fixture": "tests/fixtures/faulty_changes/demo",
        "command": ["python -c pass"],
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    "overrides",
    [
        {"blocking": False},
        {"stage": "nightly"},
        {"id": "Bad Id"},
        {"id": ""},
        {"command": []},
        {"command": [""]},
        {"command": "python -c pass"},
        {"proof_fixture": ""},
        {"command": ["python -c pass {threshold}"]},  # no threshold on the row
        {"extra": 1},
    ],
    ids=[
        "not-blocking",
        "unknown-stage",
        "bad-id",
        "empty-id",
        "empty-command-list",
        "blank-token",
        "command-not-list",
        "empty-fixture",
        "threshold-placeholder-without-threshold",
        "unknown-field",
    ],
)
def test_the_loader_rejects_malformed_rows(tmp_path: Path, overrides: dict[str, Any]) -> None:
    with pytest.raises(ConfigError):
        load_gates(_config(tmp_path, [_row(**overrides)]))


def test_the_loader_rejects_duplicate_ids(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="demo"):
        load_gates(_config(tmp_path, [_row(), _row()]))


def test_the_loader_rejects_a_document_without_gates(tmp_path: Path) -> None:
    path = build_repo(tmp_path, {"config/gates.yaml": "other: []\n"}) / "config" / "gates.yaml"
    with pytest.raises(ConfigError):
        load_gates(path)


def test_the_loader_names_the_row_in_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_gates(_config(tmp_path, [_row(), _row(id="second", stage="nightly")]))
    assert "[1]" in excinfo.value.path
