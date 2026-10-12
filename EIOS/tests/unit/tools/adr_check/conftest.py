"""Shared helpers for the adr_check tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support import decisions_repo
from tools.adr_check.repo import check_repo
from tools.common.findings import Finding


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A fresh copy of the valid fixture tree."""
    return decisions_repo.materialise(tmp_path / "repo")


@pytest.fixture
def run(repo: Path) -> Callable[[], list[Finding]]:
    """Run the check over ``repo`` (call after mutating it)."""
    return lambda: list(check_repo(repo))


def rules(findings: list[Finding]) -> set[str]:
    return {finding.rule_id for finding in findings}
