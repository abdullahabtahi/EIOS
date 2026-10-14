"""Exempt-category tests (T017), written from the taxonomy in research R-14.

The legacy auditor's temporal-exemption examples are included only as extra regression inputs.
"""

import pytest

from eios.agent_gates.core.exempt import find_exempt


def _cats(text: str, grounded: frozenset[str] = frozenset()) -> list[str]:
    spans, _ = find_exempt(text, grounded)
    return sorted(s.category for s in spans)


@pytest.mark.parametrize(
    ("text", "category"),
    [
        ("As of 2026-10-13 the ring grew.", "date_time"),
        ("Observed at 2026-10-13T16:23:00Z.", "date_time"),
        ("Updated at 12:28:54 UTC.", "date_time"),
        ("Filed on 13 October 2026.", "date_time"),
        ("Filed on Oct 13, 2026.", "date_time"),
        ("Definition v1.4.0 applies.", "version"),
        ("See version 2.3.1.", "version"),
        ("Under 31 CFR 1020.320 a report is due.", "legal_citation"),
        ("Requires FinCEN Form 111.", "legal_citation"),
        ("Per FATF Recommendation 20.", "legal_citation"),
        ("Under S.L. 373.01 of Malta.", "legal_citation"),
        ("Legal Notice 372 of 2017 applies.", "legal_citation"),
        ("See Section 5(a) of the policy.", "legal_citation"),
        ("Results for Q3 2026.", "period_label"),
        ("The FY2026 plan.", "period_label"),
        ("Your 1st and 2nd steps.", "list_marker"),
        ("There are 3 key findings across 2 sources.", "structure_count"),
        ("Three sources agree.", "structure_count"),
    ],
)
def test_taxonomy_categories_are_exempt(text: str, category: str) -> None:
    assert category in _cats(text)


def test_list_numbering_at_line_start_is_exempt() -> None:
    assert "list_marker" in _cats("1. First point\n2) Second point")


def test_a_bare_decimal_is_not_a_version() -> None:
    assert "version" not in _cats("A spread of 1.5 today.")


def test_an_identifier_a_tool_produced_is_exempt() -> None:
    spans, ungrounded = find_exempt("CR84920 shows a ring.", frozenset({"cr84920"}))
    assert [s.category for s in spans] == ["identifier"]
    assert ungrounded == []


def test_an_ungrounded_identifier_is_not_exempt_and_is_reported() -> None:
    spans, ungrounded = find_exempt("CR99999 shows a ring.", frozenset({"cr84920"}))
    assert spans == []
    assert [u.text for u in ungrounded] == ["CR99999"]


def test_identifier_shapes_cover_the_ids_in_use() -> None:
    grounded = frozenset({"ptr-882", "tok_usr_8821", "p-882"})
    for text in ("PTR-882 is at risk.", "tok_usr_8821 moved funds.", "P-882 declined."):
        assert _cats(text, grounded) == ["identifier"]
