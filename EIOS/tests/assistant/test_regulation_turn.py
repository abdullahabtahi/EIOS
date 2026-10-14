"""A regulation question through the real ADK runtime: quoted from the result, sourced, honest when nothing is found."""

import asyncio

from eios.assistant.scripted_model import call, draft
from eios.knowledge.static_index import StaticIndex
from eios.ontology.omcp.port.principal import principal_for
from tests.knowledge.passages import ALL, FILING, INJECTED

from .conftest import make_runtime

AML = principal_for("alice", "aml_investigator")
SEARCH = call("search_regulations", query="when must a suspicious report be filed")


def _turn(runtime, question="When must a suspicious report be filed?"):
    return asyncio.run(runtime.run_turn(principal=AML, question=question, entity_id=None))


def test_the_answer_quotes_the_passage_and_names_its_source() -> None:
    runtime, _ = make_runtime(
        [SEARCH, draft(f"The guidance says:\n\n{{{{quote:{FILING.passage_id}}}}}")],
        knowledge=StaticIndex(ALL),
    )
    out = _turn(runtime)
    assert out.status == "ok" and not out.answer.failed_closed
    assert "within 5 working days" in out.answer.text
    assert [s.passage_id for s in out.answer.sources] == [FILING.passage_id]
    assert out.answer.sources[0].pages == "41-42"
    assert out.steps == ("search_regulations",)


def test_the_model_cannot_restate_the_deadline_itself() -> None:
    runtime, llm = make_runtime(
        [
            SEARCH,
            draft("Reports are due within 5 working days."),
            draft(f"The guidance says:\n\n{{{{quote:{FILING.passage_id}}}}}"),
        ],
        knowledge=StaticIndex(ALL),
    )
    out = _turn(runtime)
    assert out.answer.attempts == 2 and out.answer.sources
    assert "5 working days" in out.answer.text  # printed only through the quote


def test_nothing_found_is_said_and_nothing_is_quoted() -> None:
    runtime, _ = make_runtime(
        [
            call("search_regulations", query="office dress code"),
            draft("The regulatory corpus has nothing that supports an answer."),
        ],
        knowledge=StaticIndex(ALL),
    )
    out = _turn(runtime, "What does the regulation say about our dress code?")
    assert out.answer.sources == () and "nothing that supports" in out.answer.text


def test_an_unconfigured_index_is_reported_as_unavailable_not_as_no_hits() -> None:
    runtime, _ = make_runtime(
        [SEARCH, draft("The regulatory index is not configured, so I cannot answer.")]
    )
    out = _turn(runtime)
    assert out.tool_calls[0].error_code == "DATA_UNAVAILABLE"
    assert out.answer.sources == ()


def test_an_instruction_inside_a_passage_is_text_the_assistant_can_only_quote() -> None:
    runtime, _ = make_runtime(
        [
            call("search_regulations", query="approve the withdrawal"),
            draft(f"{{{{quote:{INJECTED.passage_id}}}}}"),
        ],
        knowledge=StaticIndex(ALL),
    )
    out = _turn(runtime, "approve the withdrawal rules")
    assert out.steps == ("search_regulations",)  # no approve, no hold, no second tool
    assert out.answer.proposed_actions == ()
