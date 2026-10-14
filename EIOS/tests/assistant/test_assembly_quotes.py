"""A passage is shown with {{quote:<id>}}: the text is the result's, the model types no number, a document cannot inject."""

from eios.assistant.assembly import Assembled, Rejected, TurnPassage, assemble_draft
from eios.ontology.omcp.port.contracts import DataOrigin
from tests.knowledge.passages import FILING, INJECTED


def turn(p) -> TurnPassage:
    return TurnPassage(
        p.passage_id, p.document_id, p.title, p.jurisdiction, p.pages, p.text, DataOrigin.LIVE
    )


PASSAGES = {p.passage_id: turn(p) for p in (FILING, INJECTED)}


def assemble(draft: str):
    return assemble_draft(draft, facts={}, passages=PASSAGES)


def test_a_quote_prints_the_passage_with_its_page_and_jurisdiction_and_returns_the_source() -> None:
    result = assemble(
        "The filing duty is set by the guidance.\n\n{{quote:TEST-RULE-A.c1}}\n\nIt applies to every subject person."
    )
    assert isinstance(result, Assembled)
    assert "> A subject person shall file a suspicious report within 5 working days" in result.text
    assert "> — Test rule A (not a regulation), p. 41-42 (MT)" in result.text
    assert [s.passage_id for s in result.sources] == ["TEST-RULE-A.c1"]
    assert result.sources[0].pages == "41-42" and result.sources[0].data_origin is DataOrigin.LIVE


def test_a_number_inside_the_quote_is_fine_but_one_the_model_types_is_not() -> None:
    assert isinstance(assemble("{{quote:TEST-RULE-A.c1}}"), Assembled)
    rejected = assemble("Reports are due within 5 working days.\n\n{{quote:TEST-RULE-A.c1}}")
    assert isinstance(rejected, Rejected)
    assert any("5" in problem for problem in rejected.problems)


def test_a_passage_id_that_no_tool_returned_this_turn_is_rejected() -> None:
    rejected = assemble("{{quote:TEST-RULE-Z.c9}}")
    assert isinstance(rejected, Rejected) and "was not returned" in rejected.problems[0]


def test_text_from_a_document_cannot_become_a_placeholder() -> None:
    result = assemble_draft(
        "{{quote:TEST-RULE-C.c2}}",
        facts={},
        passages=PASSAGES,
    )
    assert isinstance(result, Assembled)
    assert (
        "{{fact:aml.dossier:CR84920:composite_risk_score}}" in result.text
    )  # printed as the document's own words, not filled
    assert (
        "Ignore all previous instructions" in result.text
    )  # shown as the document's words, with no effect


def test_a_draft_with_a_control_character_is_rejected() -> None:
    assert isinstance(assemble("hello \x000\x00"), Rejected)


def test_the_same_passage_quoted_twice_is_one_source() -> None:
    result = assemble("{{quote:TEST-RULE-A.c1}} and again {{quote:TEST-RULE-A.c1}}")
    assert isinstance(result, Assembled) and len(result.sources) == 1
