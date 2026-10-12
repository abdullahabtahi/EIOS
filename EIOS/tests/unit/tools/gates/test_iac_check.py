"""IaC gate: fmt, init (no backend) and validate per Terraform directory; tflint if present."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.support.repo_builder import build_repo
from tools.gates import _exec, iac_check

HAS_TERRAFORM = shutil.which("terraform") is not None
needs_terraform = pytest.mark.skipif(not HAS_TERRAFORM, reason="terraform is not installed")

VALID = """\
resource "terraform_data" "marker" {
  input = "ok"
}

output "marker" {
  value = terraform_data.marker.output
}
"""
UNFORMATTED = 'resource "terraform_data" "marker" {\ninput = "ok"\n}\n'
INVALID = 'output "x" {\n  value = missing_resource.nope.id\n}\n'


def test_no_infra_directory_passes_without_needing_terraform(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tools.gates._exec.find_executable", lambda _n: None)
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 0


def test_infra_without_tf_files_passes(tmp_path: Path) -> None:
    build_repo(tmp_path, {"infra/README.md": "none\n"})
    assert iac_check.find_terraform_dirs(tmp_path) == []
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 0


def test_every_directory_with_tf_files_is_found_once(tmp_path: Path) -> None:
    build_repo(
        tmp_path,
        {
            "infra/a/main.tf": VALID,
            "infra/a/other.tf": VALID,
            "infra/b/c/main.tf": VALID,
            "infra/a/.terraform/x.tf": VALID,
            "elsewhere/main.tf": VALID,
        },
    )
    found = iac_check.find_terraform_dirs(tmp_path)
    assert found == [tmp_path / "infra" / "a", tmp_path / "infra" / "b" / "c"]


def test_missing_terraform_is_a_tool_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    build_repo(tmp_path, {"infra/main.tf": VALID})
    monkeypatch.setattr("tools.gates._exec.find_executable", lambda _n: None)
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 2


@needs_terraform
def test_valid_directory_passes(tmp_path: Path) -> None:
    build_repo(tmp_path, {"infra/main.tf": VALID})
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 0


@needs_terraform
def test_invalid_definition_fails_validate(tmp_path: Path) -> None:
    build_repo(tmp_path, {"infra/ok/main.tf": VALID, "infra/broken/main.tf": INVALID})
    findings = iac_check.check_all(tmp_path)
    assert [(f.file, f.rule_id) for f in findings] == [("infra/broken", "terraform-validate")]


@needs_terraform
def test_unformatted_definition_fails_fmt(tmp_path: Path) -> None:
    build_repo(tmp_path, {"infra/main.tf": UNFORMATTED})
    findings = iac_check.check_all(tmp_path)
    assert [f.rule_id for f in findings] == ["terraform-fmt"]
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 1


@needs_terraform
def test_findings_do_not_leak_absolute_paths(tmp_path: Path) -> None:
    build_repo(tmp_path, {"infra/broken/main.tf": INVALID})
    [finding] = iac_check.check_all(tmp_path)
    assert str(tmp_path) not in finding.message
    assert str(tmp_path) not in finding.file


@needs_terraform
def test_syntax_error_is_reported_and_skips_validate(tmp_path: Path) -> None:
    build_repo(tmp_path, {"infra/main.tf": 'resource "x" {\n'})
    rules = {f.rule_id for f in iac_check.check_all(tmp_path)}
    assert "terraform-init" in rules
    assert "terraform-validate" not in rules


def _only_terraform(name: str) -> str | None:
    return "/bin/terraform" if name == "terraform" else None


def test_tflint_absence_is_tolerated_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("EIOS_REQUIRE_TFLINT", raising=False)
    monkeypatch.setattr(iac_check, "_terraform_findings", lambda _r, _d: [])
    monkeypatch.setattr(_exec, "find_executable", _only_terraform)
    build_repo(tmp_path, {"infra/main.tf": VALID})
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 0


def test_tflint_absence_fails_when_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EIOS_REQUIRE_TFLINT", "1")
    monkeypatch.setattr(iac_check, "_terraform_findings", lambda _r, _d: [])
    monkeypatch.setattr(_exec, "find_executable", _only_terraform)
    build_repo(tmp_path, {"infra/main.tf": VALID})
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 2
    assert "tflint" in capsys.readouterr().err


def test_tflint_requirement_not_enforced_with_no_terraform_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EIOS_REQUIRE_TFLINT", "1")
    assert iac_check.main(["--repo-root", str(tmp_path)]) == 0
