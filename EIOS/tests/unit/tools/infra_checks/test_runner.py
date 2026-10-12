"""`python -m tools.infra_checks` aggregates every infra check (exit 0/1/2) and writes a report."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from tests.support.infra_tree import good_files, with_file
from tests.support.repo_builder import build_repo
from tools.infra_checks.runner import TOOL_NAME, main, run_checks


def _report(root: Path) -> dict[str, object]:
    loaded: dict[str, object] = json.loads((root / f"evals/reports/{TOOL_NAME}.json").read_text())
    return loaded


def test_valid_tree_exits_0_and_writes_an_empty_report(tmp_path: Path) -> None:
    root = build_repo(tmp_path, good_files())
    assert main(["--repo-root", str(root)]) == 0
    assert _report(root)["finding_count"] == 0


def test_a_syntax_error_exits_1_with_the_parse_rule(tmp_path: Path) -> None:
    root = build_repo(tmp_path, with_file(good_files(), "infra/envs/dev/broken.tf", 'module "x" {'))
    assert main(["--repo-root", str(root)]) == 1
    assert "infra.hcl.parse" in {f.rule_id for f in run_checks(root)}


def test_a_missing_identities_file_is_one_finding_not_a_crash(tmp_path: Path) -> None:
    files = {k: v for k, v in good_files().items() if k != "infra/identities.yaml"}
    root = build_repo(tmp_path, files)
    assert {f.rule_id for f in run_checks(root)} == {"infra.identity.file"}


def test_a_tree_declaring_no_environment_topology_has_nothing_to_judge(tmp_path: Path) -> None:
    root = build_repo(tmp_path, {"infra/main.tf": 'output "marker" { value = 1 }\n'})
    assert main(["--repo-root", str(root)]) == 0
    assert run_checks(root) == ()


def test_removing_the_environment_roots_is_not_a_way_to_pass(tmp_path: Path) -> None:
    files = {k: v for k, v in good_files().items() if not k.startswith("infra/envs/")}
    root = build_repo(tmp_path, files)
    assert "infra.env.missing" in {f.rule_id for f in run_checks(root)}


def test_the_real_repository_declares_its_environment_topology() -> None:
    repo = Path(__file__).resolve().parents[4]
    assert (repo / "infra" / "envs").is_dir()
    assert (repo / "infra" / "identities.yaml").is_file()


def test_bad_arguments_exit_2(tmp_path: Path) -> None:
    assert main(["--no-such-flag"]) == 2


def test_module_entry_point_exits_with_main_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = build_repo(tmp_path, good_files())
    monkeypatch.setattr(sys, "argv", ["tools.infra_checks", "--repo-root", str(root)])
    with pytest.raises(SystemExit) as raised:
        runpy.run_module("tools.infra_checks", run_name="__main__")
    assert raised.value.code == 0
