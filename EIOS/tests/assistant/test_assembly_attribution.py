"""Which fact a plain figure cites when several returned facts share its value.

A live geo turn wrote "3 impossible jumps" and the assembler cited `gateways[1].accounts`, an unrelated fact that also
equalled 3: the figure was true but its citation was not. "22 foreign logins" was likewise cited to `exit_sessions`.
The words written right after the number now choose among equal values: the fact's unit counts twice, a word of its
own name once. With nothing to choose by, the first returned fact is cited, as before.
"""

from datetime import UTC, datetime

from eios.assistant.assembly import Assembled, TurnFact, assemble_draft
from eios.ontology.omcp.port.contracts import DataOrigin

AS_OF = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
_RAW = (  # in the order a geo account result returns them; the look-alikes come first on purpose
    ("geo.account:CR11568:gateways[1].accounts", "accounts", 3.0),
    ("geo.account:CR11568:jumps.count", "jumps", 3.0),
    ("geo.account:CR11568:exit_sessions", "sessions", 22.0),
    ("geo.account:CR11568:foreign_logins", "sessions", 22.0),
)
FACTS = {
    fid: TurnFact(fid, value, unit, AS_OF, DataOrigin.ENGINE, "geo.account")
    for fid, unit, value in _RAW
}


def _cited(draft: str) -> list[str]:
    out = assemble_draft(draft, facts=FACTS, numbers=frozenset(), trace_typed=True)
    assert isinstance(out, Assembled), out
    return [f.fact_id for f in out.figures]


def test_the_unit_written_after_the_number_picks_the_fact() -> None:
    assert _cited("The account made 3 impossible jumps.") == ["geo.account:CR11568:jumps.count"]


def test_a_word_of_the_facts_own_name_picks_it_when_the_units_agree() -> None:
    assert _cited("It logged in 22 foreign logins.") == ["geo.account:CR11568:foreign_logins"]


def test_the_same_value_cites_different_facts_in_one_answer() -> None:
    draft = "The exit is shared by 3 accounts; the account made 3 impossible jumps."
    assert _cited(draft) == [
        "geo.account:CR11568:gateways[1].accounts",
        "geo.account:CR11568:jumps.count",
    ]


def test_with_nothing_to_choose_by_the_first_returned_fact_is_cited() -> None:
    assert _cited("The count is 3.") == ["geo.account:CR11568:gateways[1].accounts"]


def test_a_plural_and_a_singular_name_the_same_unit() -> None:
    assert _cited("Only 3 jump stood out.") == ["geo.account:CR11568:jumps.count"]


def test_words_after_a_following_sentence_do_not_choose() -> None:
    # The after-window is a few words, so a unit two sentences on cannot reattribute the figure.
    assert _cited("The count is 3. Later on, the review covered many other matters and jumps.") == [
        "geo.account:CR11568:gateways[1].accounts"
    ]
