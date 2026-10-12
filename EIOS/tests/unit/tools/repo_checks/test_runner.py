"""T028/T048: `python -m tools.repo_checks` runs every enabled check (exit 0/1/2)."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from tests.support.repo_builder import build_repo
from tools.repo_checks.runner import CHECK_NAMES, main

_BIG = "x = 1\n" * 900
_PYPROJECT = '[project]\nname = "demo"\nversion = "0"\ndependencies = []\n'
_LOCK = 'version = 1\n\n[[package]]\nname = "demo"\nversion = "0"\nsource = { virtual = "." }\n'


def _run(root: Path, *extra: str) -> int:
    return main(["--repo-root", str(root), *extra])


def _report(root: Path) -> dict[str, object]:
    loaded: dict[str, object] = json.loads((root / "evals/reports/repo_checks.json").read_text())
    return loaded


def test_check_names_are_the_four_checks() -> None:
    assert CHECK_NAMES == ("file_size", "forbidden_literals", "frozen_models", "pinned_deps")


def test_bare_temp_project_passes_with_built_in_defaults(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"a.py": "x = 1\n"})
    assert _run(root) == 0
    assert _report(root)["finding_count"] == 0


def test_project_with_pyproject_and_lock_passes(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"pyproject.toml": _PYPROJECT, "uv.lock": _LOCK})
    assert _run(root) == 0


def test_project_with_pyproject_and_no_lock_exits_1(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"pyproject.toml": _PYPROJECT})
    assert _run(root) == 1
    findings = _report(root)["findings"]
    assert isinstance(findings, list)
    assert findings[0]["rule_id"] == "repo.pinned_deps"


def test_findings_from_every_check_are_aggregated(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path,
        {
            "big.py": _BIG,
            "src/eios/m.py": "from pydantic import BaseModel\n\nclass M(BaseModel):\n    x: int\n",
            "config/forbidden_literals.yaml": (
                "patterns:\n  - {id: n, regex: zzneedle, allowlist: [], reason: r}\n"
            ),
            "leak.txt": "zzneedle\n",
            "pyproject.toml": _PYPROJECT,
        },
    )
    assert _run(root) == 1
    rules = {f["rule_id"] for f in _report(root)["findings"]}  # type: ignore[attr-defined]
    assert {
        "repo.file_size",
        "repo.frozen_model",
        "repo.forbidden_literal",
        "repo.pinned_deps",
    } <= rules


def test_a_disabled_check_does_not_run(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path,
        {"big.py": _BIG, "config/repo_checks.yaml": "checks:\n  file_size: false\n"},
    )
    assert _run(root) == 0


def test_ceiling_comes_from_config(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path,
        {"a.py": "x = 1\n" * 20, "config/repo_checks.yaml": "file_size:\n  ceiling: 10\n"},
    )
    assert _run(root) == 1


def test_exclude_paths_come_from_config(tmp_path: Path) -> None:
    root = build_repo(
        tmp_path,
        {"proto/big.py": _BIG, "config/repo_checks.yaml": "exclude:\n  - proto\n"},
    )
    assert _run(root) == 0


@pytest.mark.parametrize(
    "config",
    [
        "checks:\n  unknown_check: true\n",
        "checks:\n  file_size: maybe\n",
        "file_size:\n  ceiling: 0\n",
        "surprise: 1\n",
        "checks: [unclosed\n",
    ],
)
def test_malformed_config_exits_2(tmp_path: Path, config: str) -> None:
    root = build_repo(tmp_path, {"config/repo_checks.yaml": config})
    assert _run(root) == 2


def test_malformed_forbidden_literals_config_exits_2(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"config/forbidden_literals.yaml": "patterns: 3\n"})
    assert _run(root) == 2


def test_repo_root_that_is_not_a_directory_exits_2(tmp_path: Path) -> None:
    assert _run(tmp_path / "missing") == 2


def test_module_entry_point_exits_with_the_contract_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = build_repo(tmp_path, {"big.py": _BIG})
    monkeypatch.setattr(sys, "argv", ["tools.repo_checks", "--repo-root", str(root)])
    with pytest.raises(SystemExit) as raised:
        runpy.run_module("tools.repo_checks", run_name="__main__")
    assert raised.value.code == 1
