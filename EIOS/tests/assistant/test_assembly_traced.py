"""Plain figures, checked after the fact: a number the model wrote is shown only when a tool returned it this turn.

The old rule demanded a placeholder for every figure and rejected a draft that typed one, which sent correct answers back
for another model call. Here the model may write "61.67%" or "$1.09M"; the answer is shown only if each such figure
matches (to the precision it was written at) a value a governed tool returned in this turn. A figure that matches
nothing is still rejected, so no number reaches an operator without a source.
"""

from datetime import UTC, datetime

import pytest

from eios.assistant.assembly import Assembled, Rejected, TurnFact, assemble_draft
from eios.ontology.omcp.port.contracts import DataOrigin

AS_OF = datetime(2026, 10, 14, 9, 30, tzinfo=UTC)
_RAW = {
    "partner.signals:PTR-1:churn_hazard": ("ratio", 0.6167),
    "partner.signals:PTR-1:login_decay": ("percent", 12.0),
    "partner.signals:PTR-1:volume_30d": ("USD", 1091147.74),
    "aml.dossier:AC-1:discrepancy_multiplier": ("multiplier", 16.0),
}
FACTS = {
    fid: TurnFact(fid, value, unit, AS_OF, DataOrigin.FIXTURE, "fixture.source")
    for fid, (unit, value) in _RAW.items()
}
NUMBERS = frozenset(
    {20.0, 30.0, 23.0}
)  # numbers a result held that are not figures with a unit (days left, a window, a count)


def _traced(draft: str, numbers: frozenset[float] = NUMBERS):
    return assemble_draft(draft, facts=FACTS, numbers=numbers, trace_typed=True)


@pytest.mark.parametrize(
    ("draft", "fact_id"),
    [
        ("Login decay is 12%.", "partner.signals:PTR-1:login_decay"),
        ("The churn hazard is 61.67%.", "partner.signals:PTR-1:churn_hazard"),
        ("The churn hazard is 0.62.", "partner.signals:PTR-1:churn_hazard"),
        ("The churn hazard is 0.6167.", "partner.signals:PTR-1:churn_hazard"),
        ("Volume is $1,091,147.74.", "partner.signals:PTR-1:volume_30d"),
        ("Volume is about $1.09M.", "partner.signals:PTR-1:volume_30d"),
        ("Volume is $1.1 million.", "partner.signals:PTR-1:volume_30d"),
        ("Volume is $1,091K.", "partner.signals:PTR-1:volume_30d"),
        ("A 16x discrepancy.", "aml.dossier:AC-1:discrepancy_multiplier"),
    ],
)
def test_a_figure_written_plainly_is_shown_when_a_tool_returned_it(
    draft: str, fact_id: str
) -> None:
    out = _traced(draft)
    assert isinstance(out, Assembled), out
    assert [f.fact_id for f in out.figures] == [fact_id]  # the figure keeps its provenance


def test_the_figure_is_shown_as_the_model_wrote_it_and_cites_the_governed_value() -> None:
    out = _traced("Volume is about $1.09M.")
    assert isinstance(out, Assembled)
    assert "$1.09M" in out.text
    assert out.figures[0].text == "$1.09M" and out.figures[0].value == 1091147.74


@pytest.mark.parametrize(
    "draft",
    [
        "Login decay is 13%.",  # off by one
        "The churn hazard is 0.7.",
        "Volume is $1.2M.",  # rounds to 1.2M only by being wrong
        "Volume is $2,000,000.",
        "It is 16 USD.",  # the right number with a unit no tool gave it
        "Login decay is $12.",  # a percent written as dollars
        "There are 7 accounts.",
        "About 40% of the total.",
    ],
)
def test_a_figure_no_tool_returned_is_rejected_with_the_sentence_it_is_in(draft: str) -> None:
    out = _traced(draft)
    assert isinstance(out, Rejected)
    assert any("matches no figure a tool returned" in p for p in out.problems)


def test_a_plain_number_a_result_held_without_a_unit_is_allowed_but_has_no_figure_chip() -> None:
    out = _traced("There are 20 days left on a 23 account ring.")
    assert isinstance(out, Assembled)
    assert out.figures == ()


def test_a_number_held_without_a_unit_cannot_stand_in_for_money_or_a_percentage() -> None:
    assert isinstance(_traced("It is $20."), Rejected)
    assert isinstance(_traced("It is 20%."), Rejected)
    assert isinstance(_traced("It is 20x."), Rejected)


def test_placeholders_still_work_beside_plain_figures() -> None:
    out = _traced("Decay {{fact:partner.signals:PTR-1:login_decay}} and a hazard of 61.67%.")
    assert isinstance(out, Assembled)
    assert {f.fact_id for f in out.figures} == {
        "partner.signals:PTR-1:login_decay",
        "partner.signals:PTR-1:churn_hazard",
    }


def test_dates_identifiers_and_list_numbers_are_still_not_figures() -> None:
    out = _traced("1. PTR-9699 on 2026-10-14 had a 30-day window.\n2. Next step.")
    assert isinstance(out, Assembled)


def test_a_tier_label_is_checked_like_any_other_number() -> None:
    assert isinstance(_traced("A Tier 3 partner."), Rejected)
    assert isinstance(_traced("A Tier 20 partner."), Assembled)  # 20 is a number a result held


def test_a_figure_dressed_as_a_word_hyphen_number_is_still_checked() -> None:
    assert isinstance(_traced("It is over-500 already."), Rejected)


def test_without_the_switch_a_typed_figure_is_rejected_as_before() -> None:
    out = assemble_draft("Login decay is 12%.", facts=FACTS, numbers=NUMBERS)
    assert isinstance(out, Rejected)
