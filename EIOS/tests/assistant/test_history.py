"""What the drafter is shown of earlier turns: what the operator saw, never a draft that was rejected or a raw placeholder."""

import asyncio
from types import SimpleNamespace

from google.adk.events.event import Event

from eios.assistant.answer import Answer
from eios.assistant.assembler_agent import ANSWER_METADATA_KEY, final_event
from eios.assistant.history import render_history
from eios.assistant.scripted_model import call, draft
from eios.llm_gateway.providers.adk_types import Content, Part
from eios.ontology.omcp.port.principal import principal_for

from .conftest import make_runtime

AML = principal_for("alice", "aml_investigator")
DOSSIER = call("get_aml_dossier", entity_id="CR84920")
FIGURE = "{{fact:aml.dossier:CR84920:discrepancy_multiplier}}"


def _turn(runtime, question):
    return asyncio.run(runtime.run_turn(principal=AML, question=question, entity_id="CR84920"))


def _request_text(request) -> str:
    """Everything the model was shown in one request: the instruction and every message."""
    parts = [str(request.config.system_instruction)]
    for content in request.contents:
        parts.extend(p.text for p in content.parts or [] if p.text)
    return "\n".join(parts)


def _user(text: str) -> Event:
    return Event(author="user", content=Content(role="user", parts=[Part.from_text(text=text)]))


def _answered(text: str) -> Event:
    return final_event("assembler", Answer(text=text))


def test_a_rejected_draft_is_not_shown_to_the_model_on_the_next_turn() -> None:
    runtime, llm = make_runtime(
        [DOSSIER, draft("The discrepancy is 17x."), draft(f"It is {FIGURE}."), draft("Fine.")]
    )
    first = _turn(runtime, "What is the discrepancy?")
    assert first.answer.attempts == 2 and "16x" in first.answer.text
    _turn(runtime, "And what is the next step?")
    shown = _request_text(llm.seen[-1])
    assert "17x" not in shown  # a figure no tool returned, written once by the model
    assert "{{fact:" not in shown  # a placeholder is the model's markup, not what the operator read


def test_the_model_is_shown_what_the_operator_saw() -> None:
    runtime, llm = make_runtime([DOSSIER, draft(f"It is {FIGURE}."), draft("Fine.")])
    _turn(runtime, "What is the discrepancy?")
    _turn(runtime, "And what is the next step?")
    shown = _request_text(llm.seen[-1])
    assert "What is the discrepancy?" in shown
    assert "16x" in shown  # the rendered answer, not the placeholder it came from


def test_the_current_turns_tool_results_stay_in_view_for_a_redraft() -> None:
    runtime, llm = make_runtime(
        [DOSSIER, draft("The discrepancy is 17x."), draft(f"It is {FIGURE}.")]
    )
    _turn(runtime, "What is the discrepancy?")
    retry = llm.seen[-1]
    assert any(p.function_response for c in retry.contents for p in c.parts or [])


def test_only_the_last_turns_are_kept() -> None:
    events = []
    for n in range(5):
        events += [_user(f"question {n}"), _answered(f"answer {n}")]
    events.append(_user("the current question"))
    text = render_history(events, keep=2)
    assert "question 3" in text and "answer 4" in text
    assert "question 2" not in text
    assert "the current question" not in text  # the question being answered is not history


def test_a_draft_that_was_never_assembled_is_not_history() -> None:
    drafter = Event(
        author="drafter", content=Content(role="model", parts=[Part.from_text(text="17x")])
    )
    text = render_history(
        [_user("q"), drafter, _answered("the shown answer"), _user("now")], keep=6
    )
    assert "17x" not in text and "the shown answer" in text


def test_no_history_renders_nothing() -> None:
    assert render_history([_user("the first question")], keep=6) == ""


def test_an_answer_the_assembler_marked_failed_is_still_shown_as_the_operator_saw_it() -> None:
    event = final_event(
        "assembler", Answer(text="I could not support an answer.", failed_closed=True)
    )
    assert ANSWER_METADATA_KEY in (event.custom_metadata or {})
    text = render_history([_user("q"), event, _user("now")], keep=6)
    assert "I could not support an answer." in text


def test_a_long_answer_is_trimmed_so_history_stays_small() -> None:
    text = render_history([_user("q"), _answered("x" * 5000), _user("now")], keep=6)
    assert len(text) < 2000


def test_the_instruction_tolerates_a_context_with_no_session() -> None:
    from eios.assistant.agents import instruction_for
    from eios.ontology.omcp.port.principal import Workstation

    ctx = SimpleNamespace(state={})
    assert instruction_for(Workstation.PARTNER_MANAGER, history_turns=6)(ctx)  # type: ignore[arg-type]
