"""T012: Finding shape, exit-code contract and the JSON report writer."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from eios.common.errors import ConfigError, ToolError
from tests.support.repo_builder import build_repo
from tools.common.cli import ExitCode, build_parser, exit_code_for, run_tool
from tools.common.findings import Finding
from tools.common.report import report_path, write_report


def _finding(file: str = "a.py", line: int = 3) -> Finding:
    return Finding(file=file, line=line, rule_id="R-1", message="bad thing")


def _args_tool(findings: Sequence[Finding]):  # type: ignore[no-untyped-def]
    def tool(_: argparse.Namespace) -> Sequence[Finding]:
        return findings

    return tool


# --- Finding ---------------------------------------------------------------


def test_finding_has_file_line_rule_id_message() -> None:
    finding = _finding()
    assert (finding.file, finding.line, finding.rule_id, finding.message) == (
        "a.py",
        3,
        "R-1",
        "bad thing",
    )


def test_finding_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        _finding().line = 9  # type: ignore[misc]


def test_finding_to_dict_is_a_plain_copy() -> None:
    assert _finding().to_dict() == {
        "file": "a.py",
        "line": 3,
        "rule_id": "R-1",
        "message": "bad thing",
    }


@pytest.mark.parametrize(
    ("file", "line", "rule_id", "message"),
    [
        ("", 1, "R-1", "m"),
        ("a.py", -1, "R-1", "m"),
        ("a.py", 1, "", "m"),
        ("a.py", 1, "R-1", ""),
    ],
)
def test_finding_rejects_invalid_fields(file: str, line: int, rule_id: str, message: str) -> None:
    with pytest.raises(ValueError, match="finding"):
        Finding(file=file, line=line, rule_id=rule_id, message=message)


def test_finding_rejects_non_int_line() -> None:
    with pytest.raises(ValueError, match="finding"):
        Finding(file="a.py", line="3", rule_id="R-1", message="m")  # type: ignore[arg-type]


# --- Exit codes ------------------------------------------------------------


def test_exit_code_values_are_the_contract() -> None:
    assert (int(ExitCode.PASS), int(ExitCode.FINDINGS), int(ExitCode.ERROR)) == (0, 1, 2)


def test_exit_code_for_empty_is_pass_and_non_empty_is_findings() -> None:
    assert exit_code_for([]) is ExitCode.PASS
    assert exit_code_for([_finding()]) is ExitCode.FINDINGS


def test_run_tool_returns_0_and_writes_report_on_pass(tmp_path: Path) -> None:
    code = run_tool("demo", _args_tool([]), ["--repo-root", str(tmp_path)])
    assert code == 0
    report = json.loads((tmp_path / "evals" / "reports" / "demo.json").read_text("utf-8"))
    assert report["tool"] == "demo"
    assert report["exit_code"] == 0
    assert report["findings"] == []


def test_run_tool_returns_1_and_reports_findings(tmp_path: Path) -> None:
    code = run_tool("demo", _args_tool([_finding()]), ["--repo-root", str(tmp_path)])
    assert code == 1
    report = json.loads(report_path(tmp_path, "demo").read_text("utf-8"))
    assert report["exit_code"] == 1
    assert report["findings"] == [_finding().to_dict()]


def test_run_tool_returns_2_without_traceback_on_eios_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def tool(_: argparse.Namespace) -> Sequence[Finding]:
        raise ConfigError("config/x.yaml", "gates[0]", "must be positive")

    code = run_tool("demo", tool, ["--repo-root", str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 2
    assert "config/x.yaml" in err
    assert "gates[0]" in err
    assert "Traceback" not in err
    assert not report_path(tmp_path, "demo").exists()


def test_run_tool_returns_2_on_unexpected_exception_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def tool(_: argparse.Namespace) -> Sequence[Finding]:
        raise RuntimeError("kaput")

    code = run_tool("demo", tool, ["--repo-root", str(tmp_path)])
    err = capsys.readouterr().err
    assert code == 2
    assert "RuntimeError" in err
    assert "kaput" in err
    assert "Traceback" not in err


def test_run_tool_returns_2_on_bad_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    code = run_tool("demo", _args_tool([]), ["--no-such-flag"])
    assert code == 2
    assert "Traceback" not in capsys.readouterr().err


def test_run_tool_returns_2_when_repo_root_is_not_a_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = run_tool("demo", _args_tool([]), ["--repo-root", str(tmp_path / "missing")])
    assert code == 2
    assert "missing" in capsys.readouterr().err


def test_argument_base_defaults_repo_root_to_cwd_and_accepts_extension() -> None:
    parser = build_parser("demo", "a demo tool")
    parser.add_argument("--extra", default="x")
    args = parser.parse_args([])
    assert args.repo_root == Path.cwd()
    assert args.extra == "x"


# --- Report writer ---------------------------------------------------------


def test_report_path_is_derived_from_tool_name(tmp_path: Path) -> None:
    assert report_path(tmp_path, "demo") == tmp_path / "evals" / "reports" / "demo.json"


@pytest.mark.parametrize("name", ["", "../escape", "a/b", "A B", ".hidden", "x" * 80])
def test_report_path_rejects_unsafe_tool_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(ToolError):
        report_path(tmp_path, name)


def test_write_report_creates_directory_and_deterministic_json(tmp_path: Path) -> None:
    path = write_report(tmp_path, "demo", [_finding("b.py", 2), _finding("a.py", 1)])
    assert path == report_path(tmp_path, "demo")
    report = json.loads(path.read_text("utf-8"))
    assert report["tool"] == "demo"
    assert report["exit_code"] == 1
    assert report["finding_count"] == 2
    assert [f["file"] for f in report["findings"]] == ["a.py", "b.py"]


def test_write_report_replaces_its_own_previous_report(tmp_path: Path) -> None:
    write_report(tmp_path, "demo", [_finding()])
    path = write_report(tmp_path, "demo", [])
    assert json.loads(path.read_text("utf-8"))["finding_count"] == 0
    assert [p.name for p in path.parent.iterdir()] == ["demo.json"]


def test_write_report_never_overwrites_another_tools_report(tmp_path: Path) -> None:
    other = json.dumps({"tool": "other", "exit_code": 0, "finding_count": 0, "findings": []})
    build_repo(tmp_path, {"evals/reports/demo.json": other})
    with pytest.raises(ToolError, match="other"):
        write_report(tmp_path, "demo", [])
    assert (tmp_path / "evals" / "reports" / "demo.json").read_text("utf-8") == other


@pytest.mark.parametrize("content", ["{not json", "[]", '{"no_tool": 1}'])
def test_write_report_refuses_to_overwrite_unrecognised_report(
    tmp_path: Path, content: str
) -> None:
    build_repo(tmp_path, {"evals/reports/demo.json": content})
    with pytest.raises(ToolError):
        write_report(tmp_path, "demo", [])
    assert (tmp_path / "evals" / "reports" / "demo.json").read_text("utf-8") == content


def test_write_report_does_not_mutate_input_findings(tmp_path: Path) -> None:
    findings = [_finding("b.py", 2), _finding("a.py", 1)]
    snapshot = list(findings)
    write_report(tmp_path, "demo", findings)
    assert findings == snapshot
