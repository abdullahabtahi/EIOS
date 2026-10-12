"""The valid fixture passes; unrelated shapes do not trip the check."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from tests.support import decisions_repo as dr
from tools.common.findings import Finding


def test_valid_tree_has_no_findings(run: Callable[[], list[Finding]]) -> None:
    assert run() == []


def test_proposed_adr_needs_no_decision_or_evidence(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    assert "## Decision\n\n\n" in (repo / "docs/adr/003-graph-engine.md").read_text("utf-8")
    assert run() == []


def test_proposed_and_open_index_entries_without_file_pass(
    run: Callable[[], list[Finding]],
) -> None:
    # ADR-002 (Open) and ADR-006 (Proposed) have no file in the fixture.
    assert run() == []


def test_template_files_are_skipped(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.write(repo, "docs/adr/_template-adr.md", "# ADR-NNN: Title\n")
    dr.write(repo, "docs/adr/_template-spike.md", "# S-NN: Title\n")
    assert run() == []
