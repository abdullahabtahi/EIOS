"""The open-decision engine is config-driven: a second decision is a config section, no code."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tests.support.open_decision_repo import (
    CONFIG_RELATIVE,
    INDEX_RELATIVE,
    adr_index_text,
)
from tests.support.repo_builder import build_repo
from tools.common.findings import Finding
from tools.open_decision_check.engine import main, run_checks

_SECOND = """\
decisions:
  - adr: ADR-099
    rules:
      - id: fake_sdk
        kind: import_root
        modules: [fakesdk, fakecorp.client]
      - id: fake_names
        kind: bound_value
        patterns: ['zzname-[0-9]+']
    allowed_paths: [src/ok/]
    lifted_when:
      lifted: {lifted}
      adr_status: Accepted
  - adr: ADR-098
    rules:
      - id: other_sdk
        kind: import_root
        modules: [othersdk]
    allowed_paths: []
    lifted_when:
      lifted: false
      adr_status: Accepted
"""


def _config(lifted: str = "false", scan: str = "") -> str:
    return scan + _SECOND.replace("{lifted}", lifted)


def _tree(
    config: str, files: dict[str, str] | None = None, index: str | None = None
) -> dict[str, str]:
    return {
        CONFIG_RELATIVE: config,
        INDEX_RELATIVE: index or adr_index_text({"ADR-099": "Open", "ADR-098": "Open"}),
        **(files or {}),
    }


def _run(tmp_path: Path, tree: dict[str, str]) -> list[Finding]:
    return list(run_checks(build_repo(tmp_path, tree)))


def test_a_second_synthetic_decision_is_enforced_with_no_code_change(tmp_path: Path) -> None:
    files = {
        "src/a.py": "import fakesdk\n",
        "src/b.py": "from fakecorp import client\n",
        "src/c.py": "x = 'zzname-7'\n",
        "src/d.py": "import othersdk\n",
        "src/ok/e.py": "import fakesdk\nx = 'zzname-7'\n",
    }
    findings = _run(tmp_path, _tree(_config(), files))
    got = sorted((f.file, f.line, f.rule_id) for f in findings)
    assert got == [
        ("src/a.py", 1, "open_decision.ADR-099.fake_sdk"),
        ("src/b.py", 1, "open_decision.ADR-099.fake_sdk"),
        ("src/c.py", 1, "open_decision.ADR-099.fake_names"),
        ("src/d.py", 1, "open_decision.ADR-098.other_sdk"),
    ]


def test_decisions_are_lifted_independently(tmp_path: Path) -> None:
    index = adr_index_text({"ADR-099": "Accepted", "ADR-098": "Open"})
    files = {"src/a.py": "import fakesdk\n", "src/d.py": "import othersdk\n"}
    findings = _run(tmp_path, _tree(_config("true"), files, index))
    assert [(f.file, f.rule_id) for f in findings] == [
        ("src/d.py", "open_decision.ADR-098.other_sdk")
    ]


def test_scan_include_and_exclude_come_from_config(tmp_path: Path) -> None:
    scan = "scan:\n  include: ['.py']\n  exclude: [src/skipped]\n"
    files = {
        "src/a.txt": "zzname-1\n",
        "src/skipped/b.py": "import fakesdk\n",
        "src/c.py": "import fakesdk\n",
    }
    findings = _run(tmp_path, _tree(_config(scan=scan), files))
    assert [f.file for f in findings] == ["src/c.py"]


def test_include_may_name_exact_files(tmp_path: Path) -> None:
    scan = "scan:\n  include: [Dockerfile]\n"
    files = {"app/Dockerfile": "ENV X=zzname-1\n", "app/other.txt": "zzname-1\n"}
    findings = _run(tmp_path, _tree(_config(scan=scan), files))
    assert [f.file for f in findings] == ["app/Dockerfile"]


def test_non_text_files_are_skipped(tmp_path: Path) -> None:
    root = build_repo(tmp_path, _tree(_config()))
    (root / "blob.yaml").write_bytes(b"\xff\xfe\x00zzname-1")
    assert list(run_checks(root)) == []


def test_symlinked_files_are_never_followed(tmp_path: Path) -> None:
    root = build_repo(tmp_path, _tree(_config(), {"real/a.py": "import fakesdk\n"}))
    (root / "src").mkdir()
    (root / "src" / "link.py").symlink_to(root / "real" / "a.py")
    assert [f.file for f in run_checks(root)] == ["real/a.py"]


# --- configuration errors fail closed (exit 2 path) -----------------------------------------


def _error(tmp_path: Path, tree: dict[str, str]) -> str:
    with pytest.raises(ConfigError) as caught:
        run_checks(build_repo(tmp_path, tree))
    return str(caught.value)


def test_missing_config_is_an_error(tmp_path: Path) -> None:
    assert "open_decisions.yaml" in _error(tmp_path, {"a.txt": ""})


@pytest.mark.parametrize(
    ("config", "fragment"),
    [
        ("decisions: []\n", "decisions"),
        ("nothing: 1\n", "decisions"),
        ("- not a mapping\n", "$"),
        (_config().replace("adr: ADR-099", "adr: nope"), "adr"),
        (_config().replace("kind: import_root", "kind: telepathy", 1), "telepathy"),
        (_config().replace("modules: [fakesdk, fakecorp.client]", "modules: []", 1), "modules"),
        (_config().replace("[fakesdk, fakecorp.client]", "[not valid!]", 1), "modules"),
        (_config().replace("['zzname-[0-9]+']", "['(unclosed']", 1), "patterns"),
        (_config().replace("['zzname-[0-9]+']", "[]", 1), "patterns"),
        (_config().replace("adr_status: Accepted", "adr_status: Maybe", 1), "adr_status"),
        (_config().replace("    allowed_paths: [src/ok/]\n", "", 1), "allowed_paths"),
        (_config().replace("adr: ADR-098", "adr: ADR-099"), "duplicate"),
        (_config().replace("id: fake_names", "id: fake_sdk"), "duplicate"),
        (_config().replace("lifted: false", "lifted: yes-ish", 1), "lifted"),
        (_config() + "surprise: 1\n", "surprise"),
    ],
)
def test_invalid_config_is_rejected_with_a_located_message(
    tmp_path: Path, config: str, fragment: str
) -> None:
    assert fragment in _error(tmp_path, _tree(config))


def test_rule_without_its_parameter_is_rejected(tmp_path: Path) -> None:
    config = _config().replace("        modules: [fakesdk, fakecorp.client]\n", "", 1)
    message = _error(tmp_path, _tree(config))
    assert "modules" in message
    assert "decisions[0].rules[0]" in message


def test_non_string_parameter_entries_are_rejected(tmp_path: Path) -> None:
    config = _config().replace("[fakesdk, fakecorp.client]", "[fakesdk, 7]", 1)
    assert "modules" in _error(tmp_path, _tree(config))


def test_lift_needs_a_readable_index_with_the_decision(tmp_path: Path) -> None:
    assert INDEX_RELATIVE in _error(tmp_path, {CONFIG_RELATIVE: _config("true")})
    no_row = {CONFIG_RELATIVE: _config("true"), INDEX_RELATIVE: adr_index_text({"ADR-001": "x"})}
    assert "ADR-099" in _error(tmp_path / "b", no_row)


def test_index_is_not_read_while_every_decision_is_unlifted(tmp_path: Path) -> None:
    assert _run(tmp_path, {CONFIG_RELATIVE: _config()}) == []


# --- command line ----------------------------------------------------------------------------


def test_main_exit_codes_and_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clean = build_repo(tmp_path / "clean", _tree(_config()))
    assert main(["--repo-root", str(clean)]) == 0
    dirty = build_repo(tmp_path / "dirty", _tree(_config(), {"src/a.py": "import fakesdk\n"}))
    assert main(["--repo-root", str(dirty)]) == 1
    report = json.loads((dirty / "evals" / "reports" / "open_decision_check.json").read_text())
    assert report["tool"] == "open_decision_check"
    assert report["findings"][0]["file"] == "src/a.py"
    assert report["findings"][0]["line"] == 1
    broken = build_repo(tmp_path / "broken", {"a.txt": ""})
    assert main(["--repo-root", str(broken)]) == 2
    assert "open_decision_check: error" in capsys.readouterr().err


def test_python_dash_m_entry_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = build_repo(tmp_path, _tree(_config()))
    monkeypatch.setattr(sys, "argv", ["open_decision_check", "--repo-root", str(root)])
    with pytest.raises(SystemExit) as caught:
        runpy.run_module("tools.open_decision_check", run_name="__main__")
    assert caught.value.code == 0
