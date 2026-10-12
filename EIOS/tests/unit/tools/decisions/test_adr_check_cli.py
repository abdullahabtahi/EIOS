"""``python -m tools.adr_check``: exit codes 0/1/2 and the JSON report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.support import decisions_repo as dr
from tools.adr_check.__main__ import main


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return dr.materialise(tmp_path / "repo")


def _report(root: Path) -> dict[str, object]:
    data = json.loads((root / "evals" / "reports" / "adr_check.json").read_text("utf-8"))
    assert isinstance(data, dict)
    return data


def test_valid_tree_exits_zero_and_writes_report(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--repo-root", str(repo)]) == 0
    report = _report(repo)
    assert report["tool"] == "adr_check"
    assert report["findings"] == []
    assert "adr_check" in capsys.readouterr().out


def test_findings_exit_one_and_are_in_report(repo: Path) -> None:
    dr.remove(repo, "docs/adr/001-ontology.md")
    assert main(["--repo-root", str(repo)]) == 1
    findings = _report(repo)["findings"]
    assert isinstance(findings, list)
    assert findings[0]["rule_id"] == "adr.index.missing_file"


def test_missing_index_is_a_config_error(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    dr.remove(repo, "docs/spikes_and_adrs.md")
    assert main(["--repo-root", str(repo)]) == 2
    assert "docs/spikes_and_adrs.md" in capsys.readouterr().err


def test_bad_repo_root_exits_two(tmp_path: Path) -> None:
    assert main(["--repo-root", str(tmp_path / "nope")]) == 2
