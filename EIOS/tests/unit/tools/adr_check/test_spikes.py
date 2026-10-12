"""Spike validation: open spikes need little, closed spikes need a result and a live ADR."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.support import decisions_repo as dr
from tests.unit.tools.adr_check.conftest import rules
from tools.common.findings import Finding

CLOSED = "docs/adr/S-01-graph-ceiling.md"
OPEN = "docs/adr/S-02-model-availability.md"


def test_open_spike_needs_only_question_time_box_owner(
    run: Callable[[], list[Finding]],
) -> None:
    assert run() == []


@pytest.mark.parametrize(
    ("label", "rule"),
    [
        ("Question", "spike.field.question"),
        ("Time box", "spike.field.time_box"),
        ("Owner", "spike.field.owner"),
    ],
)
def test_open_spike_missing_required(
    repo: Path, run: Callable[[], list[Finding]], label: str, rule: str
) -> None:
    text = (repo / OPEN).read_text(encoding="utf-8")
    kept = "".join(line for line in text.splitlines(keepends=True) if not line.startswith(label))
    dr.write(repo, OPEN, kept)
    found = [f for f in run() if f.rule_id == rule]
    assert [f.file for f in found] == [OPEN]


@pytest.mark.parametrize(
    ("label", "rule"),
    [
        ("Method", "spike.field.method"),
        ("Data", "spike.field.data"),
        ("Result", "spike.field.result"),
        ("Decision", "spike.field.decision"),
        ("Date", "spike.field.date"),
        ("Outcome", "spike.field.outcome"),
        ("Linked ADR", "spike.field.linked_adr"),
    ],
)
def test_closed_spike_requires_each_field(
    repo: Path, run: Callable[[], list[Finding]], label: str, rule: str
) -> None:
    text = (repo / CLOSED).read_text(encoding="utf-8")
    kept = "".join(
        line for line in text.splitlines(keepends=True) if not line.startswith(f"{label}:")
    )
    dr.write(repo, CLOSED, kept)
    assert rule in rules(run())


def test_closed_spike_without_linked_adr_is_rejected(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, CLOSED, "Linked ADR: ADR-003\n", "")
    assert rules(run()) == {"spike.field.linked_adr"}


def test_closed_spike_linking_open_adr_is_rejected(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, CLOSED, "Linked ADR: ADR-003", "Linked ADR: ADR-002")
    assert rules(run()) == {"spike.link.adr_open"}


def test_closed_spike_linking_unknown_adr_is_rejected(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, CLOSED, "Linked ADR: ADR-003", "Linked ADR: ADR-099")
    assert rules(run()) == {"spike.link.adr_unknown"}


def test_closed_spike_linking_adr_without_file_but_proposed_passes(
    repo: Path, run: Callable[[], list[Finding]]
) -> None:
    dr.replace(repo, CLOSED, "Linked ADR: ADR-003", "Linked ADR: ADR-006")
    assert run() == []


@pytest.mark.parametrize("spike_id", ["S-1", "S-001", "X-01", "s-01"])
def test_invalid_spike_id(repo: Path, run: Callable[[], list[Finding]], spike_id: str) -> None:
    dr.replace(repo, OPEN, "Id: S-02", f"Id: {spike_id}")
    assert "spike.field.id" in rules(run())


def test_spike_id_must_match_filename(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, OPEN, "Id: S-02", "Id: S-09")
    assert "spike.field.id" in rules(run())


def test_invalid_state(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, OPEN, "State: open", "State: pending")
    assert rules(run()) == {"spike.field.state"}


def test_closed_spike_date_must_be_iso(repo: Path, run: Callable[[], list[Finding]]) -> None:
    dr.replace(repo, CLOSED, "Date: 2026-01-10", "Date: 10 Jan")
    assert rules(run()) == {"spike.field.date"}
