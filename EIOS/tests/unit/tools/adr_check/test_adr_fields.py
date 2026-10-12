"""ADR field validation: one distinct rule id per violated field."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support import decisions_repo as dr
from tests.unit.tools.adr_check.conftest import rules
from tools.common.findings import Finding

ACCEPTED = "docs/adr/001-ontology.md"
PROPOSED = "docs/adr/003-graph-engine.md"


def _blank_section(repo: Path, relative: str, heading: str) -> None:
    text = (repo / relative).read_text(encoding="utf-8")
    start = text.index(f"## {heading}\n") + len(f"## {heading}\n")
    end = text.find("\n## ", start)
    end = len(text) if end == -1 else end
    dr.write(repo, relative, text[:start] + "\n" + text[end:])


@pytest.mark.parametrize(
    ("heading", "rule"),
    [
        ("Status", "adr.field.status"),
        ("Date", "adr.field.date"),
        ("Context", "adr.field.context"),
        ("Options considered", "adr.field.options"),
        ("Decision", "adr.field.decision"),
        ("Consequences", "adr.field.consequences"),
        ("Evidence", "adr.field.evidence"),
        ("Revisit when", "adr.field.revisit_when"),
    ],
)
def test_empty_field_reports_its_rule(
    repo: Path, run: Callable[[], list[Finding]], heading: str, rule: str
) -> None:
    _blank_section(repo, ACCEPTED, heading)
    found = [f for f in run() if f.rule_id == rule]
    assert [f.file for f in found] == [ACCEPTED]
    assert "empty" in found[0].message


def test_missing_field_heading_is_reported_as_missing(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, ACCEPTED, "## Revisit when", "## Something else")
    found = [f for f in run() if f.rule_id == "adr.field.revisit_when"]
    assert found
    assert "missing" in found[0].message


def test_accepted_without_evidence_fails_only_for_accepted(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    _blank_section(repo, ACCEPTED, "Evidence")
    assert rules(run()) == {"adr.field.evidence"}


def test_fewer_than_two_options_fails(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, ACCEPTED, "- B: the alternative, drawback is a larger surface\n", "")
    found = run()
    assert rules(found) == {"adr.field.options"}
    assert "two" in found[0].message


def test_inline_lettered_options_count(repo: Path, run: Callable[[], list[Finding]]) -> None:
    text = (repo / ACCEPTED).read_text(encoding="utf-8")
    start = text.index("- A:")
    end = text.index("\n## Decision")
    dr.write(repo, ACCEPTED, text[:start] + "A) first option. B) second option.\n" + text[end:])
    assert run() == []


def test_decision_required_when_superseded(repo: Path, run: Callable[[], list[Finding]]) -> None:
    _blank_section(repo, "docs/adr/004-approval-v1.md", "Decision")
    assert rules(run()) == {"adr.field.decision"}


@pytest.mark.parametrize("status", ["Open", "Accepted.", "Superseded", "accepted", "Done"])
def test_invalid_status_value(repo: Path, run: Callable[[], list[Finding]], status: str) -> None:
    dr.replace(repo, PROPOSED, "## Status\n\nProposed", f"## Status\n\n{status}")
    assert "adr.field.status" in rules(run())


@pytest.mark.parametrize("date", ["05/01/2026", "2026-13-01", "2026-1-5", "yesterday"])
def test_invalid_date(repo: Path, run: Callable[[], list[Finding]], date: str) -> None:
    dr.replace(repo, ACCEPTED, "2026-01-05", date)
    assert rules(run()) == {"adr.field.date"}


def test_title_number_must_match_filename(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, ACCEPTED, "# ADR-001:", "# ADR-009:")
    assert "adr.field.number" in rules(run())


def test_title_must_have_adr_heading(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, ACCEPTED, "# ADR-001: Ontology as data and logic", "# Ontology")
    assert "adr.field.title" in rules(run())


def test_badly_named_adr_file(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.write(repo, "docs/adr/7-short.md", "# ADR-007: Short\n")
    assert "adr.filename" in rules(run())


def test_html_comment_does_not_count_as_content(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, ACCEPTED, "Forces and constraints for this decision.", "<!-- fill in -->")
    assert rules(run()) == {"adr.field.context"}
