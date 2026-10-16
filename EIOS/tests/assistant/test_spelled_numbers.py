"""Numbers in words are figures: read like the judge reads them, and checked by the assembler like digits."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from eios.agent_gates.core.exempt import find_exempt
from eios.agent_gates.core.figures import extract_figures
from eios.assistant.assembly import Assembled, Rejected, TurnFact, assemble_draft
from eios.assistant.spelled_numbers import spelled_numbers
from eios.ontology.omcp.port.contracts import DataOrigin

AS_OF = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
FACTS = {
    "geo.account:CR11568:login_country_count": TurnFact(
        "geo.account:CR11568:login_country_count", 2.0, "countries", AS_OF, DataOrigin.ENGINE, "geo"
    ),
    "geo.list_change:fatf:added.exposed_accounts": TurnFact(
        "geo.list_change:fatf:added.exposed_accounts",
        3_000_000.0,
        "USD",
        AS_OF,
        DataOrigin.ENGINE,
        "geo",
    ),
}


def _assemble(draft: str):
    return assemble_draft(draft, facts=FACTS, numbers=frozenset(), trace_typed=True)


@pytest.mark.parametrize(
    ("text", "values"),
    [
        ("logged in from two countries", [2.0]),
        ("twenty-three accounts", [23.0]),
        ("three hundred and five sessions", [305.0]),
        ("three million dollars", [3_000_000.0]),
        ("one of the exits", []),  # "one" alone is not a figure
        ("a million", []),  # a bare scale word is not a figure
        ("four-eyes approval", []),  # not every part is a number word
        ("two sources and three key findings", []),  # the answer counting its own structure
        ("four analytical lenses", [4.0]),
    ],
)
def test_the_reader_agrees_with_the_judge(text: str, values: list[float]) -> None:
    ours = [s.value * s.scale for s in spelled_numbers(text)]
    assert ours == values
    masked = [(s.start, s.end) for s in find_exempt(text)[0]]
    judges = [f.value for f in extract_figures(text, masked) if f.spelled]
    assert judges == values


def test_a_count_the_model_made_itself_is_sent_back() -> None:
    out = _assemble("The account logged in from four countries.")
    assert isinstance(out, Rejected)
    assert any("four" in p for p in out.problems)


def test_a_count_a_tool_returned_may_be_written_in_words_and_is_cited() -> None:
    out = _assemble("The account logged in from two countries.")
    assert isinstance(out, Assembled)
    assert [f.fact_id for f in out.figures] == ["geo.account:CR11568:login_country_count"]


def test_a_scaled_figure_in_words_matches_at_the_precision_written() -> None:
    assert isinstance(_assemble("About three million dollars moved."), Assembled)
    assert isinstance(_assemble("About four million dollars moved."), Rejected)


def test_words_that_are_not_figures_pass_untouched() -> None:
    assert isinstance(
        _assemble("A four-eyes approval is needed; one of the exits is shared."), Assembled
    )
