"""IaC gate (T050): format, init (no backend) and validate every Terraform directory.

``tflint`` is used when installed. Setting ``EIOS_REQUIRE_TFLINT=1`` (CI does) turns its
absence into a tool error, so a missing linter can never silently pass the gate.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from eios.common.errors import ToolError
from tools.common.cli import run_tool
from tools.common.findings import Finding
from tools.gates import _exec

INFRA_DIR = "infra"
REQUIRE_TFLINT_ENV = "EIOS_REQUIRE_TFLINT"
_TF_ENV = {"TF_IN_AUTOMATION": "1", "TF_INPUT": "0", "CHECKPOINT_DISABLE": "1"}
_SUMMARY_LIMIT = 400


def find_terraform_dirs(repo_root: Path) -> list[Path]:
    """Directories under ``infra/`` holding ``*.tf`` files (provider caches excluded)."""
    infra = repo_root / INFRA_DIR
    if not infra.is_dir():
        return []
    found = {
        tf.parent
        for tf in infra.rglob("*.tf")
        if tf.is_file() and ".terraform" not in tf.relative_to(infra).parts
    }
    return sorted(found)


def _summary(root: Path, *texts: str) -> str:
    squeezed = " ".join(" ".join(texts).replace(str(root), ".").split())
    return squeezed[:_SUMMARY_LIMIT] or "no output"


def _step(root: Path, directory: Path, rule: str, argv: Sequence[str]) -> Finding | None:
    """Run one terraform step; a non-zero exit becomes a finding on the directory."""
    result = _exec.run(argv, directory, extra_env=_TF_ENV)
    if result.returncode == 0:
        return None
    where = directory.relative_to(root).as_posix()
    return Finding(where, 0, rule, _summary(root, result.stdout, result.stderr))


def _terraform_findings(root: Path, directory: Path) -> list[Finding]:
    terraform = _exec.require_executable("terraform")
    findings: list[Finding] = []
    fmt = _step(root, directory, "terraform-fmt", [terraform, "fmt", "-check", "-no-color"])
    if fmt is not None:
        findings.append(fmt)
    init = [terraform, "init", "-backend=false", "-input=false", "-no-color"]
    failed_init = _step(root, directory, "terraform-init", init)
    if failed_init is not None:
        return [*findings, failed_init]
    validate = _step(root, directory, "terraform-validate", [terraform, "validate", "-no-color"])
    return [*findings, validate] if validate is not None else findings


def _tflint_findings(root: Path, directory: Path, tflint: str) -> list[Finding]:
    finding = _step(
        root, directory, "terraform-tflint", [tflint, "--no-color", "--minimum-failure-severity=error"]
    )
    return [finding] if finding is not None else []


def check_all(repo_root: Path) -> list[Finding]:
    directories = find_terraform_dirs(repo_root)
    if not directories:
        return []
    _exec.require_executable("terraform")
    tflint = _exec.find_executable("tflint")
    if tflint is None and os.environ.get(REQUIRE_TFLINT_ENV) == "1":
        raise ToolError(f"tflint is required ({REQUIRE_TFLINT_ENV}=1) but not on PATH")
    findings: list[Finding] = []
    for directory in directories:
        findings.extend(_terraform_findings(repo_root, directory))
        if tflint is not None:
            findings.extend(_tflint_findings(repo_root, directory, tflint))
    return findings


def _run(args: argparse.Namespace) -> Sequence[Finding]:
    return check_all(args.repo_root.resolve())


def main(argv: Sequence[str]) -> int:
    return run_tool("iac_check", _run, argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
