"""Which entity a question is about, and whether it asks for the full picture (intent.py)."""

from __future__ import annotations

import pytest

from eios.assistant.intent import is_broad, named_entity, resolve_entity
from eios.assistant.prefetch import plan
from eios.ontology.omcp.port.principal import Workstation

PARTNER = Workstation.PARTNER_MANAGER
AML = Workstation.AML_INVESTIGATOR


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Expound on PTR 9699", "PTR-9699"),
        ("expound on ptr-9699 please", "PTR-9699"),
        ("What about AP-1029?", "AP-1029"),
        ("Why is this partner at risk?", None),
        ("How many partners are there? 1029", None),
    ],
)
def test_a_partner_id_is_read_as_the_system_writes_it(question: str, expected: str | None) -> None:
    assert named_entity(PARTNER, question) == expected


def test_an_account_id_is_read_from_the_question() -> None:
    assert named_entity(AML, "Tell me about cr 84920") == "CR84920"
    assert named_entity(AML, "Tell me about this account") is None
    assert named_entity(Workstation.EXECUTIVE, "PTR-9699?") is None


def test_the_entity_the_question_names_wins_over_the_one_on_screen() -> None:
    assert resolve_entity(PARTNER, "Expound on PTR 9699", "PTR-8809") == ("PTR-9699", "PTR-9699")
    assert resolve_entity(PARTNER, "Expound on PTR 8809", "PTR-8809") == ("PTR-8809", None)
    assert resolve_entity(PARTNER, "Why is it at risk?", "PTR-8809") == ("PTR-8809", None)
    assert resolve_entity(PARTNER, "Why is it at risk?", None) == (None, None)


@pytest.mark.parametrize(
    "question",
    [
        "Expound on PTR 9699",
        "Tell me more about this",
        "What should I do about it?",
        "Brief me on it",
    ],
)
def test_a_broad_question_is_recognised(question: str) -> None:
    assert is_broad(question)


@pytest.mark.parametrize(
    "question", ["Why is this partner at risk?", "What's the reason?", "Who is it?"]
)
def test_a_narrow_question_is_not_broad(question: str) -> None:
    assert not is_broad(question)


def test_a_broad_partner_question_also_checks_integrity_in_the_same_step() -> None:
    assert plan(PARTNER, "Expound on this partner", "PTR-9699") == [
        ("get_partner_signals", {"entity_id": "PTR-9699"}),
        ("get_partner_integrity", {"entity_id": "PTR-9699"}),
    ]
    assert plan(PARTNER, "Why is this partner at risk?", "PTR-9699") == [
        ("get_partner_signals", {"entity_id": "PTR-9699"})
    ]
