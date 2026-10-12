"""Index/file agreement: one distinct rule per failure class."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from tests.support import decisions_repo as dr
from tests.unit.tools.adr_check.conftest import rules
from tools.common.findings import Finding


def test_accepted_index_entry_without_file_fails(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.remove(repo, "docs/adr/001-ontology.md")
    found = run()
    assert rules(found) == {"adr.index.missing_file"}
    assert "ADR-001" in found[0].message


def test_superseded_index_entry_without_file_fails(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.remove(repo, "docs/adr/004-approval-v1.md")
    assert "adr.index.missing_file" in rules(run())


def test_file_without_index_entry_fails(repo: Path, run: Callable[[], list[Finding]]) -> None:
    text = (repo / "docs/adr/003-graph-engine.md").read_text(encoding="utf-8")
    dr.write(repo, "docs/adr/007-extra.md", text.replace("ADR-003", "ADR-007"))
    found = run()
    assert rules(found) == {"adr.index.missing_entry"}
    assert found[0].file == "docs/adr/007-extra.md"


def test_status_mismatch_fails(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(
        repo,
        "docs/spikes_and_adrs.md",
        "| Graph engine choice | Proposed |",
        "| Graph engine choice | Accepted |",
    )
    assert rules(run()) == {"adr.index.status_mismatch"}


def test_title_mismatch_fails(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, "docs/spikes_and_adrs.md", "Graph engine choice", "Graph database pick")
    assert rules(run()) == {"adr.index.title_mismatch"}


def test_title_comparison_ignores_case_and_spacing(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, "docs/spikes_and_adrs.md", "Graph engine choice", "graph  Engine choice.")
    assert run() == []


def test_duplicate_index_number_fails(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(
        repo,
        "docs/spikes_and_adrs.md",
        "| ADR-006 | Ledger anchors |",
        "| ADR-003 | Ledger anchors |",
    )
    assert "adr.index.duplicate_number" in rules(run())


def test_duplicate_file_number_fails(repo: Path, run: Callable[[], list[Finding]]) -> None:
    text = (repo / "docs/adr/003-graph-engine.md").read_text(encoding="utf-8")
    dr.write(repo, "docs/adr/003-graph-engine-copy.md", text)
    assert "adr.index.duplicate_number" in rules(run())


def test_one_way_supersession_predecessor_names_successor_only(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, "docs/adr/005-approval-v2.md", "ADR-004", "")
    found = run()
    assert rules(found) == {"adr.supersession.one_way"}
    assert "ADR-004" in found[0].message


def test_one_way_supersession_successor_names_predecessor_only(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(
        repo,
        "docs/adr/004-approval-v1.md",
        "## Status\n\nSuperseded by ADR-005",
        "## Status\n\nAccepted",
    )
    dr.replace(repo, "docs/spikes_and_adrs.md", "Superseded by ADR-005", "Accepted")
    assert rules(run()) == {"adr.supersession.one_way"}


def test_supersession_to_missing_successor_file_fails(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.remove(repo, "docs/adr/005-approval-v2.md")
    found = rules(run())
    assert "adr.supersession.missing_successor" in found


def test_supersedes_unknown_adr_fails(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, "docs/adr/005-approval-v2.md", "ADR-004", "ADR-004, ADR-042")
    assert "adr.supersession.unknown_target" in rules(run())
