"""``python -m tools.open_decision_check``: exit codes 0/1/2, decision lines and the report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.open_decision_repo import (
    ALL_OPEN,
    CONFIG_RELATIVE,
    INDEX_RELATIVE,
    all_open_tree,
    config_with_lift,
    stub_tree,
    with_files,
)
from tests.support.repo_builder import build_repo
from tools.open_decision_check.engine import main

PROTOTYPE_PATHS = ["FEIOS", "DESIGN.MD", "DESIGN_PLAN.md", "web-prototype"]


def _report(root: Path) -> dict[str, object]:
    data = json.loads((root / "evals" / "reports" / "open_decision_check.json").read_text("utf-8"))
    assert isinstance(data, dict)
    return data


def test_clean_tree_exits_zero_and_reports_each_decision_open(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = build_repo(tmp_path, all_open_tree())
    assert main(["--repo-root", str(root)]) == 0
    out = capsys.readouterr().out
    for adr in ALL_OPEN:
        assert f"{adr}: open (index status Open)" in out
    for path in PROTOTYPE_PATHS:
        assert f"excluded prototype path: {path}" in out
    report = _report(root)
    assert report["tool"] == "open_decision_check"
    assert report["findings"] == []
    assert report["decisions"] == {
        adr: {"state": "open", "index_status": "Open"} for adr in ALL_OPEN
    }
    assert report["excluded_prototype_paths"] == PROTOTYPE_PATHS


def test_a_violation_exits_one_and_is_in_the_report(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path, with_files(all_open_tree(), {"schema.graphql": "type Q {a: Int}\n"})
    )
    assert main(["--repo-root", str(root)]) == 1
    findings = _report(root)["findings"]
    assert isinstance(findings, list)
    assert [f["rule_id"] for f in findings] == ["open_decision.ADR-014.graphql_schema_files"]


def test_prototype_paths_are_not_scanned_but_still_listed(tmp_path: Path) -> None:
    tree = with_files(all_open_tree(), {"web-prototype/schema.graphql": "type Q {a: Int}\n"})
    root = build_repo(tmp_path, tree)
    assert main(["--repo-root", str(root)]) == 0
    assert _report(root)["excluded_prototype_paths"] == PROTOTYPE_PATHS


def test_a_lifted_decision_is_reported_lifted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = stub_tree({**ALL_OPEN, "ADR-009": "Accepted"})
    tree[CONFIG_RELATIVE] = config_with_lift("ADR-009", lifted=True)
    root = build_repo(tmp_path, tree)
    assert main(["--repo-root", str(root)]) == 0
    assert "ADR-009: lifted (index status Accepted)" in capsys.readouterr().out
    assert _report(root)["decisions"]["ADR-009"]["state"] == "lifted"  # type: ignore[index]


def test_a_config_lift_the_index_does_not_allow_is_called_out(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = all_open_tree()
    tree[CONFIG_RELATIVE] = config_with_lift("ADR-003", lifted=True)
    root = build_repo(tmp_path, tree)
    assert main(["--repo-root", str(root)]) == 1
    line = next(x for x in capsys.readouterr().out.splitlines() if x.startswith("ADR-003"))
    assert line.startswith("ADR-003: open") and "index does not allow it" in line


def test_a_missing_config_is_a_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = all_open_tree()
    del tree[CONFIG_RELATIVE]
    root = build_repo(tmp_path, tree)
    assert main(["--repo-root", str(root)]) == 2
    assert "open_decisions.yaml" in capsys.readouterr().err


def test_an_invalid_config_is_a_tool_error(tmp_path: Path) -> None:
    tree = all_open_tree()
    tree[CONFIG_RELATIVE] = "decisions: not-a-list\n"
    assert main(["--repo-root", str(build_repo(tmp_path, tree))]) == 2


def test_a_missing_index_is_reported_unavailable_while_nothing_is_lifted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = all_open_tree()
    del tree[INDEX_RELATIVE]
    root = build_repo(tmp_path, tree)
    assert main(["--repo-root", str(root)]) == 0
    assert "ADR-003: open (index status unavailable)" in capsys.readouterr().out


def test_a_lift_with_a_missing_index_is_a_tool_error(tmp_path: Path) -> None:
    tree = all_open_tree()
    del tree[INDEX_RELATIVE]
    tree[CONFIG_RELATIVE] = config_with_lift("ADR-003", lifted=True)
    assert main(["--repo-root", str(build_repo(tmp_path, tree))]) == 2


def test_bad_repo_root_exits_two(tmp_path: Path) -> None:
    assert main(["--repo-root", str(tmp_path / "nope")]) == 2
