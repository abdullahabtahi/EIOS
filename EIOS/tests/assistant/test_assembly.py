"""The answer assembler: figures come from governed results, never from the model's own text (spec 021 FR-001..003)."""

from datetime import UTC, datetime

import pytest

from eios.assistant.assembly import (
    FAIL_CLOSED_TEXT,
    MAX_ATTEMPTS,
    Assembled,
    Rejected,
    TurnFact,
    assemble_draft,
    fail_closed_answer,
)
from eios.ontology.omcp.port.contracts import DataOrigin

AS_OF = datetime(2026, 10, 14, 9, 30, tzinfo=UTC)
_RAW = {
    "aml.dossier:AC-1:discrepancy_multiplier": ("multiplier", 16.0),
    "aml.dossier:AC-1:exposure_usd": ("USD", 1234567.0),
    "metric.get:churn@PTR-882:value": ("percent", 12.5),
    "aml.dossier:AC-1:open_alerts": ("alerts", 3.0),
}
FACTS = {
    fid: TurnFact(fid, value, unit, AS_OF, DataOrigin.FIXTURE, "fixture.source")
    for fid, (unit, value) in _RAW.items()
}


def _assemble(draft: str, facts: dict[str, TurnFact] | None = None):
    return assemble_draft(draft, facts=FACTS if facts is None else facts)


def test_a_placeholder_is_replaced_by_the_governed_figure_with_its_unit() -> None:
    out = _assemble(
        "The discrepancy is {{fact:aml.dossier:AC-1:discrepancy_multiplier}} on this account."
    )
    assert isinstance(out, Assembled)
    assert "16x" in out.text
    assert "{{" not in out.text
    assert [f.fact_id for f in out.figures] == ["aml.dossier:AC-1:discrepancy_multiplier"]


@pytest.mark.parametrize(
    ("fact_id", "expected"),
    [
        ("aml.dossier:AC-1:exposure_usd", "$1,234,567"),
        ("metric.get:churn@PTR-882:value", "12.5%"),
        ("aml.dossier:AC-1:open_alerts", "3 alerts"),
    ],
)
def test_units_are_rendered_beside_the_figure(fact_id: str, expected: str) -> None:
    out = _assemble(f"Value: {{{{fact:{fact_id}}}}}.")
    assert isinstance(out, Assembled)
    assert expected in out.text


def test_demo_data_and_as_of_are_stated_once_not_per_figure() -> None:
    out = _assemble(
        "{{fact:aml.dossier:AC-1:discrepancy_multiplier}} and {{fact:aml.dossier:AC-1:exposure_usd}}."
    )
    assert isinstance(out, Assembled)
    assert out.text.lower().count("demo data") == 1
    assert "2026-10-14" in out.text


def test_a_figure_the_model_typed_itself_is_rejected() -> None:
    out = _assemble("The discrepancy is 16x and exposure is $1.2M.")
    assert isinstance(out, Rejected)
    assert any("16" in p for p in out.problems)


def test_a_typed_figure_beside_a_valid_placeholder_is_still_rejected() -> None:
    out = _assemble("{{fact:aml.dossier:AC-1:open_alerts}} alerts, about 40% of the total.")
    assert isinstance(out, Rejected)


def test_a_fact_id_not_returned_this_turn_is_rejected_even_if_it_exists() -> None:
    only_alerts = {"aml.dossier:AC-1:open_alerts": FACTS["aml.dossier:AC-1:open_alerts"]}
    out = _assemble("{{fact:aml.dossier:AC-1:exposure_usd}}", only_alerts)
    assert isinstance(out, Rejected)
    assert any("exposure_usd" in p for p in out.problems)


def test_an_invented_fact_id_is_rejected() -> None:
    out = _assemble("{{fact:aml.dossier:AC-1:made_up}}")
    assert isinstance(out, Rejected)


def test_dates_identifiers_and_list_numbers_are_not_figures() -> None:
    out = _assemble(
        "1. Review account AC-1 on 15 March 2026.\n2. Discrepancy {{fact:aml.dossier:AC-1:discrepancy_multiplier}}."
    )
    assert isinstance(out, Assembled)


def test_a_malformed_placeholder_is_rejected_not_printed() -> None:
    out = _assemble("Exposure {{fact:}} and {{fact:aml.dossier:AC-1:exposure_usd")
    assert isinstance(out, Rejected)


def test_an_empty_draft_is_rejected() -> None:
    assert isinstance(_assemble("   "), Rejected)


def test_a_draft_with_no_figures_is_accepted_and_has_no_demo_footer_claim_of_figures() -> None:
    out = _assemble("That is outside this workstation.")
    assert isinstance(out, Assembled)
    assert out.figures == ()


def test_fail_closed_answer_has_no_figure_and_none_of_the_models_numbers() -> None:
    answer = fail_closed_answer(DataOrigin.FIXTURE)
    assert answer.text.startswith(FAIL_CLOSED_TEXT)
    assert answer.figures == ()
    assert answer.failed_closed is True
    assert not any(ch.isdigit() for ch in answer.text)
    assert MAX_ATTEMPTS == 3


@pytest.mark.parametrize(
    "draft",
    [
        "Volume was top-10 of all accounts.",
        "Exposure is USD500000 today.",
        "Exposure is over-500 today.",
        "The risk_87 band applies.",
        "It moved 3x since USDT8000 arrived.",
    ],
)
def test_a_number_dressed_as_an_identifier_is_still_a_typed_figure(draft: str) -> None:
    assert isinstance(_assemble(draft), Rejected), draft


@pytest.mark.parametrize(
    ("draft", "shown"),
    [
        ("It is {{fact:aml.dossier:AC-1:discrepancy_multiplier}}x the declared income.", "16x the"),
        ("Exposure is {{fact:aml.dossier:AC-1:exposure_usd}} USD today.", "$1,234,567 today"),
        ("Churn is {{fact:metric.get:churn@PTR-882:value}} percent.", "12.5%."),
    ],
)
def test_a_unit_repeated_after_a_placeholder_is_not_shown_twice(draft: str, shown: str) -> None:
    out = _assemble(draft)
    assert isinstance(out, Assembled)
    assert shown in out.text


def test_a_word_that_only_starts_like_a_unit_is_kept() -> None:
    out = _assemble("There are {{fact:aml.dossier:AC-1:open_alerts}} xylophone alerts.")
    assert isinstance(out, Assembled)
    assert "3 alerts xylophone alerts" in out.text
