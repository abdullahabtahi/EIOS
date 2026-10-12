"""T014: read-only parsers for ADR files, spike files and the decision/spike index tables."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from eios.common.errors import ConfigError
from tools.records.adr import parse_adr
from tools.records.index import parse_adr_index, parse_spike_index
from tools.records.markdown import ABSENT, Absent, FieldValue, parse_table, split_sections
from tools.records.spike import parse_spike

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "records"
REAL_INDEX = REPO_ROOT / "docs" / "spikes_and_adrs.md"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _text(value: FieldValue) -> str:
    """Narrow a parsed field to str, failing the test if it is the absent marker."""
    assert isinstance(value, str), "expected text, got ABSENT"
    return value


# --------------------------------------------------------------------------- markdown helpers


def test_absent_marker_is_distinct_from_empty_string() -> None:
    empty: object = ""
    assert ABSENT != empty
    assert isinstance(ABSENT, Absent)
    assert not ABSENT
    assert Absent() == ABSENT


def test_split_sections_splits_on_level_two_headings_only() -> None:
    text = "# Title\nintro\n## One\nbody one\n### Sub\nsub body\n## Two\nbody two\n"
    sections = split_sections(text)
    assert [s.heading for s in sections] == ["One", "Two"]
    assert "sub body" in sections[0].body


def test_split_sections_ignores_headings_inside_code_fences() -> None:
    text = "## Real\n```\n## Fake\n```\n"
    assert [s.heading for s in split_sections(text)] == ["Real"]


def test_parse_table_returns_rows_keyed_by_header() -> None:
    body = "text\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n\nafter\n"
    assert parse_table(body) == (
        {"A": "1", "B": "2"},
        {"A": "3", "B": "4"},
    )


def test_parse_table_without_a_table_returns_empty_tuple() -> None:
    assert parse_table("no table here\n") == ()


def test_parse_table_ignores_tables_inside_code_fences() -> None:
    assert parse_table("```\n| A |\n|---|\n| 1 |\n```\n") == ()


def test_parse_table_rejects_row_with_wrong_cell_count() -> None:
    with pytest.raises(ValueError, match="cells"):
        parse_table("| A | B |\n|---|---|\n| only-one |\n")


# --------------------------------------------------------------------------- ADR files


def test_parse_adr_labelled_template_style_all_fields() -> None:
    adr = parse_adr(_fixture("adr_labelled.md"), source="docs/adr/004-graph-engine.md")
    assert adr.source == "docs/adr/004-graph-engine.md"
    assert adr.adr_id == "ADR-004"
    assert adr.title == "Graph engine for ring detection"
    assert adr.status == "Accepted"
    assert adr.date == "2026-03-14"
    assert _text(adr.context).startswith("Ring detection needs community search")
    assert "Hub nodes (shared IPs) cause false merges." in _text(adr.context)
    assert adr.options == "A) NetworkX with hub suppression. B) Managed graph database."
    assert adr.decision == "Use NetworkX with hub suppression for the POC."
    assert adr.consequences == "Positive: no new service. Negative: memory ceiling."
    assert adr.evidence == "S-05, benchmark report in evals/graph."
    assert adr.revisit_when == "graph exceeds the measured ceiling."


def test_parse_adr_heading_style_all_fields() -> None:
    adr = parse_adr(_fixture("adr_headings.md"), source="docs/adr/010-approval.md")
    assert adr.adr_id == "ADR-010"
    assert adr.title == "Approval service hosting"
    assert adr.status == "Superseded by ADR-020"
    assert adr.date == "2026-01-05"
    assert (
        adr.context
        == "Approvals need a durable, single-use intent store.\n\nSecond paragraph of context."
    )
    assert adr.options == "- A: Cloud Run plus Firestore\n- B: Self-managed queue"
    assert adr.decision == "Cloud Run plus Firestore."
    assert adr.evidence == "S-06"
    assert adr.revisit_when == "Approval volume exceeds the free tier."


def test_parse_adr_missing_sections_are_absent_not_empty() -> None:
    adr = parse_adr(_fixture("adr_partial.md"), source="x.md")
    assert adr.evidence is ABSENT
    assert adr.revisit_when is ABSENT
    assert adr.consequences == "Cached results can be stale."


def test_parse_adr_present_but_empty_section_is_empty_string_not_absent() -> None:
    adr = parse_adr(_fixture("adr_partial.md"), source="x.md")
    assert adr.decision == ""
    assert isinstance(adr.decision, str)


def test_parse_adr_empty_text_gives_all_absent() -> None:
    adr = parse_adr("", source="empty.md")
    assert adr.source == "empty.md"
    for value in (
        adr.adr_id,
        adr.title,
        adr.status,
        adr.date,
        adr.context,
        adr.options,
        adr.decision,
        adr.consequences,
        adr.evidence,
        adr.revisit_when,
    ):
        assert value is ABSENT


def test_parse_adr_heading_without_adr_number_keeps_text_as_title() -> None:
    adr = parse_adr("# Just a title\nStatus: Proposed\n", source="x.md")
    assert adr.adr_id is ABSENT
    assert adr.title == "Just a title"


def test_parse_adr_returns_status_as_found_without_validating() -> None:
    adr = parse_adr("# ADR-001: T\nStatus: Banana\n", source="x.md")
    assert adr.status == "Banana"


def test_parse_adr_handles_unicode_and_bold_labels() -> None:
    text = "# ADR-007: Ledger ✓ tamper-evidence \U0001f512\n**Status:** Accepted\n"
    adr = parse_adr(text, source="x.md")
    assert adr.title == "Ledger ✓ tamper-evidence \U0001f512"
    assert adr.status == "Accepted"


def test_parse_adr_ignores_label_words_inside_code_fences() -> None:
    text = "# ADR-001: T\nContext: real\n```\nDecision: fenced\n```\n"
    adr = parse_adr(text, source="x.md")
    assert adr.decision is ABSENT
    assert "Decision: fenced" in _text(adr.context)


def test_adr_record_is_frozen() -> None:
    adr = parse_adr("# ADR-001: T\n", source="x.md")
    with pytest.raises(FrozenInstanceError):
        adr.status = "Accepted"  # type: ignore[misc]


# --------------------------------------------------------------------------- spike files


def test_parse_spike_contract_fields() -> None:
    spike = parse_spike(_fixture("spike_closed.md"), source="docs/adr/S-05.md")
    assert spike.source == "docs/adr/S-05.md"
    assert spike.spike_id == "S-05"
    assert _text(spike.question).startswith("Where is the memory and time ceiling")
    assert spike.time_box == "1 day [TARGET]"
    assert spike.owner == "platform-team"
    assert spike.outcome == "Ceiling measured at the stated edge count."
    assert spike.linked_adr == "ADR-004"
    assert spike.state == "closed"


def test_parse_spike_data_model_fields() -> None:
    spike = parse_spike(_fixture("spike_closed.md"), source="x.md")
    assert _text(spike.method).startswith("Generate graphs from 10k to 1M edges")
    assert spike.data == "Synthetic graphs, seed 7."
    assert _text(spike.result).startswith("Build time grows linearly")
    assert spike.decision == "Keep NetworkX for the POC."
    assert spike.date == "2026-03-10"


def test_parse_spike_accepts_status_and_unlocks_aliases_in_heading_style() -> None:
    spike = parse_spike(_fixture("spike_data_model_fields.md"), source="x.md")
    assert spike.spike_id == "S-02"
    assert spike.question == "Cube Core or a lightweight registry over DuckDB?"
    assert spike.state == "open"
    assert spike.linked_adr == "ADR-003"
    assert spike.owner == "data-platform"


def test_parse_spike_missing_fields_are_absent() -> None:
    spike = parse_spike(_fixture("spike_data_model_fields.md"), source="x.md")
    assert spike.time_box is ABSENT
    assert spike.outcome is ABSENT
    assert spike.method is ABSENT
    assert spike.date is ABSENT


def test_parse_spike_empty_text_gives_all_absent() -> None:
    spike = parse_spike("", source="empty.md")
    assert spike.spike_id is ABSENT
    assert spike.question is ABSENT
    assert spike.linked_adr is ABSENT
    assert spike.state is ABSENT


def test_parse_spike_id_label_wins_over_heading() -> None:
    spike = parse_spike("# S-09: Heading\nId: S-10\n", source="x.md")
    assert spike.spike_id == "S-10"


def test_spike_record_is_frozen() -> None:
    spike = parse_spike("# S-01: T\n", source="x.md")
    with pytest.raises(FrozenInstanceError):
        spike.state = "closed"  # type: ignore[misc]


# --------------------------------------------------------------------------- real index tables


def test_parse_real_adr_index_contains_open_decisions() -> None:
    rows = {r.adr_id: r for r in parse_adr_index(REAL_INDEX.read_text(encoding="utf-8"))}
    for adr_id in ("ADR-002", "ADR-003", "ADR-009", "ADR-014"):
        assert adr_id in rows
        assert rows[adr_id].status == "Open"


def test_parse_real_adr_index_strips_emphasis_and_keeps_other_statuses() -> None:
    rows = {r.adr_id: r for r in parse_adr_index(REAL_INDEX.read_text(encoding="utf-8"))}
    assert rows["ADR-009"].decision == "Frontend stack & design system"
    assert rows["ADR-001"].status == "Accepted"
    assert rows["ADR-004"].status == "Proposed"
    assert rows["ADR-002"].depends_on == "S-01"
    assert rows["ADR-002"].depends_on_spikes == ("S-01",)
    assert rows["ADR-010"].depends_on_spikes == ()


def test_parse_real_spike_index_contains_s01_with_linked_adr() -> None:
    rows = {r.spike_id: r for r in parse_spike_index(REAL_INDEX.read_text(encoding="utf-8"))}
    assert "S-01" in rows
    assert rows["S-01"].question.startswith("Which LLM(s), model IDs")
    assert rows["S-01"].unlocks_adrs == ("ADR-002",)
    assert rows["S-06"].unlocks_adrs == ("ADR-006", "ADR-007")


def test_real_index_rows_are_unique_and_ordered_as_in_the_file() -> None:
    text = REAL_INDEX.read_text(encoding="utf-8")
    adr_ids = [r.adr_id for r in parse_adr_index(text)]
    spike_ids = [r.spike_id for r in parse_spike_index(text)]
    assert adr_ids == sorted(set(adr_ids))
    assert spike_ids == sorted(set(spike_ids))


# --------------------------------------------------------------------------- index error paths

_ADR_TABLE = (
    "## 2. ADR index\n\n"
    "| ADR | Decision | Status | Default / current lean | Depends on |\n"
    "|---|---|---|---|---|\n"
    "| ADR-001 | One | Accepted | lean | — |\n"
)
_SPIKE_TABLE = (
    "## 1. Spikes\n\n"
    "| ID | Question | Why unverified | Method | Decision it unlocks | Fallback |\n"
    "|---|---|---|---|---|---|\n"
    "| **S-01** | Q? | why | how | ADR-002 (x) | fb |\n"
)


def test_parse_adr_index_on_minimal_table() -> None:
    rows = parse_adr_index(_ADR_TABLE)
    assert len(rows) == 1
    assert rows[0].adr_id == "ADR-001"
    assert rows[0].default_or_current_lean == "lean"
    assert rows[0].depends_on_spikes == ()


def test_parse_spike_index_on_minimal_table() -> None:
    rows = parse_spike_index(_SPIKE_TABLE)
    assert [r.spike_id for r in rows] == ["S-01"]
    assert rows[0].fallback == "fb"


def test_parse_adr_index_missing_section_raises_config_error() -> None:
    with pytest.raises(ConfigError) as info:
        parse_adr_index("## Something else\n", source="idx.md")
    assert info.value.file == "idx.md"
    assert "ADR index" in str(info.value)


def test_parse_spike_index_missing_section_raises_config_error() -> None:
    with pytest.raises(ConfigError) as info:
        parse_spike_index("", source="idx.md")
    assert info.value.file == "idx.md"


def test_parse_adr_index_section_without_table_raises_config_error() -> None:
    with pytest.raises(ConfigError, match="table"):
        parse_adr_index("## 2. ADR index\n\njust prose\n", source="idx.md")


def test_parse_adr_index_missing_column_raises_config_error() -> None:
    text = "## 2. ADR index\n\n| ADR | Decision |\n|---|---|\n| ADR-001 | One |\n"
    with pytest.raises(ConfigError, match="Status"):
        parse_adr_index(text, source="idx.md")


def test_parse_adr_index_ragged_row_raises_config_error() -> None:
    text = _ADR_TABLE + "| ADR-002 | broken |\n"
    with pytest.raises(ConfigError, match="cells"):
        parse_adr_index(text, source="idx.md")


def test_index_parsers_do_not_confuse_the_two_tables() -> None:
    both = _SPIKE_TABLE + "\n" + _ADR_TABLE
    assert [r.adr_id for r in parse_adr_index(both)] == ["ADR-001"]
    assert [r.spike_id for r in parse_spike_index(both)] == ["S-01"]
