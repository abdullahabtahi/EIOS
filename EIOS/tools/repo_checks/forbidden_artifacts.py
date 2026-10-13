"""Fail when a Terraform plan or state file, or a private key file, is tracked by git.

A Terraform plan embeds a snapshot of state (API keys, hash configuration, resource attributes), so
committing one leaks what the secret scanners cannot read inside a binary. Only tracked files count:
ignored local files are fine. Outside a git checkout the tree is walked instead.
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from tools.common.findings import Finding
from tools.repo_checks._walk import iter_files, relative_posix

RULE_ID = "repo.forbidden_artifact"

_PATTERNS = (
    "tfplan",
    "*.tfplan",
    "*.tfstate",
    "*.tfstate.*",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.jks",
    "id_rsa",
    "id_ed25519",
)


def _tracked_files(repo_root: Path) -> list[str] | None:
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "ls-files", "-z"],  # noqa: S607
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except OSError, subprocess.CalledProcessError:
        return None
    return [p for p in result.stdout.decode("utf-8", "replace").split("\0") if p]


def _is_forbidden(relative: str) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in _PATTERNS)


def check_forbidden_artifacts(repo_root: Path) -> tuple[Finding, ...]:
    root = repo_root.resolve()
    tracked = _tracked_files(root)
    candidates = (
        tracked if tracked is not None else [relative_posix(root, p) for p in iter_files(root)]
    )
    return tuple(
        Finding(
            file=relative,
            line=0,
            rule_id=RULE_ID,
            message="Terraform plan/state and private key files must not be tracked; they embed credentials",
        )
        for relative in sorted(candidates)
        if _is_forbidden(relative)
    )
