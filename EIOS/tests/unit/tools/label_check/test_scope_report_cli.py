from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support.label_repo import materialise
from tests.support.repo_builder import build_repo
from tools.label_check.__main__ import main
from tools.label_check.scanner import scan_repo


def _report(root: Path) -> dict[str, object]:
    data: dict[str, object] = json.loads(
        (root / "evals" / "reports" / "label_check.json").read_text("utf-8")
    )
    return data


def test_clean_run_exits_zero_prints_count_and_writes_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = materialise("clean", tmp_path / "r")
    assert main(["--repo-root", str(root)]) == 0
    assert "scanned 2 files, 0 findings" in capsys.readouterr().out
    report = _report(root)
    assert report["tool"] == "label_check" and report["scanned_count"] == 2
    assert report["spike_states"] == {"S-01": "open"}


def test_findings_exit_one(tmp_path: Path) -> None:
    root = materialise("clean", tmp_path / "r")
    build_repo(root, {"docs/bad.md": "Churn rose 12%.\n"})
    assert main(["--repo-root", str(root)]) == 1
    assert _report(root)["finding_count"] == 1


def test_missing_config_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build_repo(tmp_path, {"docs/a.md": "Plain.\n"})
    assert main(["--repo-root", str(tmp_path)]) == 2
    assert "label_check: error" in capsys.readouterr().err


def test_scope_globs_brief_source_and_prototype_exclusions(tmp_path: Path) -> None:
    root = materialise("clean", tmp_path / "r")
    unlabelled = "Churn rose 12%.\n"
    build_repo(
        root,
        {
            "docs/brief/extra.md": unlabelled,
            "docs/evidence/run.md": unlabelled,
            "FEIOS/docs/p.md": unlabelled,
            "DESIGN.MD": unlabelled,
            "notes/outside.md": unlabelled,
            "specs/001/spec.md": unlabelled,
        },
    )
    result = scan_repo(root)
    assert [f.file for f in result.findings] == ["specs/001/spec.md"]
    assert "docs/brief/extra.md" not in result.scanned
    assert {"FEIOS/", "DESIGN.MD", "DESIGN_PLAN.md"} <= set(result.excluded)
    assert "docs/brief/" in result.excluded
