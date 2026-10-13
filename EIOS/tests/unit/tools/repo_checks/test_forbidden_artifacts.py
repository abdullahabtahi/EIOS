"""State, plan and key files must never be tracked: they embed credentials and resource snapshots."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.repo_checks.forbidden_artifacts import RULE_ID, check_forbidden_artifacts


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _repo(tmp_path: Path, files: dict[str, str], *, track: bool = True) -> Path:
    for name, content in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    if track:
        _git(tmp_path, "init", "-q")
        _git(tmp_path, "add", "-A", "-f")
    return tmp_path


@pytest.mark.parametrize(
    "name",
    [
        "infra/envs/prod-like/tfplan",
        "infra/out.tfplan",
        "infra/terraform.tfstate",
        "infra/terraform.tfstate.backup",
        "secrets/server.pem",
        "secrets/client.p12",
        "keys/id_rsa",
    ],
)
def test_tracked_artifacts_are_flagged(tmp_path: Path, name: str) -> None:
    root = _repo(tmp_path, {name: "x", "README.md": "ok"})
    findings = check_forbidden_artifacts(root)
    assert [f.file for f in findings] == [name]
    assert findings[0].rule_id == RULE_ID


def test_clean_repo_and_examples_pass(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"main.tf": "x", "terraform.tfvars.example": "x", "docs/plan.md": "x"})
    assert check_forbidden_artifacts(root) == ()


def test_untracked_local_files_are_not_flagged(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"main.tf": "x"})
    (root / "tfplan").write_text("local only", encoding="utf-8")  # present on disk, never added
    assert check_forbidden_artifacts(root) == ()


def test_without_git_it_falls_back_to_walking_the_tree(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"infra/tfplan": "x"}, track=False)
    assert [f.file for f in check_forbidden_artifacts(root)] == ["infra/tfplan"]


def test_standalone_subcommand_fails_on_a_tracked_plan_and_writes_its_own_report(
    tmp_path: Path,
) -> None:
    """The plan/state/key guard runs as its own gate, so quarantining lint cannot switch it off."""
    import json

    from tools.repo_checks.runner import main

    clean = _repo(tmp_path / "clean", {"infra/main.tf": "# ok\n"})
    assert main(["forbidden-artifacts", "--repo-root", str(clean)]) == 0

    leaked = _repo(
        tmp_path / "leaked", {"infra/main.tf": "# ok\n", "infra/tfplan": "state snapshot"}
    )
    assert main(["forbidden-artifacts", "--repo-root", str(leaked)]) == 1
    report = json.loads((leaked / "evals/reports/forbidden_artifacts.json").read_text())
    assert [f["file"] for f in report["findings"]] == ["infra/tfplan"]
    assert main(["forbidden-artifacts", "--repo-root", str(leaked / "missing")]) == 2
