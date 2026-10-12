"""Dependency advisory gate: lock export, pip-audit output parsing, error paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eios.common.errors import ToolError
from tests.support.repo_builder import build_repo
from tools.gates import vuln_scan

CLEAN = {"dependencies": [{"name": "good", "version": "1.0", "vulns": []}], "fixes": []}
VULNERABLE = {
    "dependencies": [
        {"name": "good", "version": "1.0", "vulns": []},
        {
            "name": "bad",
            "version": "0.1",
            "vulns": [
                {"id": "PYSEC-0000-1", "fix_versions": ["0.2", "0.3"], "aliases": ["CVE-0-1"]},
                {"id": "GHSA-xxxx", "fix_versions": [], "aliases": []},
            ],
        },
    ],
    "fixes": [],
}


def test_clean_audit_has_no_findings() -> None:
    assert vuln_scan.parse_audit(json.dumps(CLEAN)) == []


def test_each_advisory_becomes_a_finding_on_the_lockfile() -> None:
    findings = vuln_scan.parse_audit(json.dumps(VULNERABLE))
    assert [f.rule_id for f in findings] == ["PYSEC-0000-1", "GHSA-xxxx"]
    assert {f.file for f in findings} == {"uv.lock"}
    assert "bad==0.1" in findings[0].message
    assert "0.2" in findings[0].message


def test_repeated_advisories_for_one_pin_are_reported_once() -> None:
    doubled = {"dependencies": [*VULNERABLE["dependencies"], *VULNERABLE["dependencies"]]}
    assert len(vuln_scan.parse_audit(json.dumps(doubled))) == 2


def test_advisory_without_fix_says_so() -> None:
    findings = vuln_scan.parse_audit(json.dumps(VULNERABLE))
    assert "no fix" in findings[1].message


@pytest.mark.parametrize("text", ["", "not json", "[]", "{}", '{"dependencies": 3}', "null"])
def test_malformed_audit_output_is_a_tool_error(text: str) -> None:
    with pytest.raises(ToolError):
        vuln_scan.parse_audit(text)


def test_skipped_dependencies_are_reported_not_hidden() -> None:
    text = json.dumps({"dependencies": [{"name": "x", "skip_reason": "not on PyPI"}]})
    findings = vuln_scan.parse_audit(text)
    assert findings == []
    assert vuln_scan.skipped_dependencies(text) == ["x: not on PyPI"]


def test_missing_lockfile_is_a_tool_error(tmp_path: Path) -> None:
    build_repo(tmp_path, {"pyproject.toml": "[project]\nname='x'\nversion='0'\n"})
    with pytest.raises(ToolError, match=r"uv\.lock"):
        vuln_scan.audit(tmp_path)


def test_audit_combines_export_and_pip_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_repo(tmp_path, {"uv.lock": "", "pyproject.toml": ""})
    seen: list[str] = []

    def fake_export(_root: Path) -> str:
        return "bad==0.1\n"

    def fake_audit(requirements: str, _root: Path) -> str:
        seen.append(requirements)
        return json.dumps(VULNERABLE)

    monkeypatch.setattr(vuln_scan, "_export_requirements", fake_export)
    monkeypatch.setattr(vuln_scan, "_run_pip_audit", fake_audit)
    findings = vuln_scan.audit(tmp_path)
    assert seen == ["bad==0.1\n"]
    assert len(findings) == 2


def test_main_exit_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_repo(tmp_path, {"uv.lock": "", "pyproject.toml": ""})
    monkeypatch.setattr(vuln_scan, "_export_requirements", lambda _r: "")
    monkeypatch.setattr(vuln_scan, "_run_pip_audit", lambda _t, _r: json.dumps(CLEAN))
    assert vuln_scan.main(["--repo-root", str(tmp_path)]) == 0
    monkeypatch.setattr(vuln_scan, "_run_pip_audit", lambda _t, _r: json.dumps(VULNERABLE))
    assert vuln_scan.main(["--repo-root", str(tmp_path)]) == 1


def test_main_exit_2_without_lockfile(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert vuln_scan.main(["--repo-root", str(tmp_path)]) == 2
    assert "uv.lock" in capsys.readouterr().err


@pytest.mark.requires_network
def test_real_audit_of_the_repository_lock_completes() -> None:
    repo = Path(__file__).resolve().parents[4]
    findings = vuln_scan.audit(repo)
    assert isinstance(findings, list)
