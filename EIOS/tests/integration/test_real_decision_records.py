"""The real decision records, spike records and feature register pass the new checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.label_repo import REPO_ROOT
from tools.adr_check.repo import check_repo
from tools.records.adr import parse_adr
from tools.records.index import parse_adr_index, parse_spike_index

BACKFILLED = ("001", "006", "007", "010", "011", "012", "013", "015")
OPEN_ADRS = ("ADR-002", "ADR-003", "ADR-008", "ADR-009", "ADR-014")


def _index() -> str:
    return (REPO_ROOT / "docs" / "spikes_and_adrs.md").read_text(encoding="utf-8")


def test_real_records_pass_adr_check() -> None:
    assert [(f.file, f.rule_id) for f in check_repo(REPO_ROOT)] == []


def test_every_accepted_adr_has_a_backfilled_record() -> None:
    accepted = {r.adr_id for r in parse_adr_index(_index()) if r.status == "Accepted"}
    files = {p.name[:3]: p for p in (REPO_ROOT / "docs" / "adr").glob("[0-9]*.md")}
    assert accepted == {f"ADR-{number}" for number in BACKFILLED}
    for number in BACKFILLED:
        record = parse_adr(files[number].read_text(encoding="utf-8"), str(files[number]))
        assert "backfilled" in str(record.evidence).lower()


def test_every_spike_is_open_with_a_record() -> None:
    rows = parse_spike_index(_index())
    assert [r.spike_id for r in rows] == [f"S-0{n}" for n in range(1, 8)]
    for row in rows:
        assert list((REPO_ROOT / "docs" / "adr").glob(f"{row.spike_id}-*.md"))


@pytest.mark.parametrize("adr_id", OPEN_ADRS)
def test_open_decisions_stay_open(adr_id: str) -> None:
    status = {r.adr_id: r.status for r in parse_adr_index(_index())}[adr_id]
    assert status == "Open"


def test_feature_register_lists_f00_to_f15() -> None:
    text = Path(REPO_ROOT / "docs" / "feature_register.yaml").read_text(encoding="utf-8")
    for number in range(16):
        assert f"F{number:02d}" in text
