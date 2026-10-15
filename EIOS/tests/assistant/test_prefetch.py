"""The platform runs the obvious tool before the model speaks: one model call, the same governed result, honest when wrong."""

import asyncio
from dataclasses import replace

from eios.assistant.config import AssistantSettings
from eios.assistant.prefetch import plan
from eios.assistant.runtime import AssistantRuntime
from eios.assistant.scripted_model import ScriptedLlm, call, draft
from eios.assistant.sessions import build_session_service
from eios.knowledge.static_index import StaticIndex
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import Workstation, principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from tests.knowledge.passages import ALL, FILING

ON = AssistantSettings.from_env(
    {"EIOS_ENVIRONMENT": "test", "EIOS_ASSISTANT_TURN_DEADLINE_S": "10"}
)
AML = principal_for("alice", "aml_investigator")
FIGURE = "{{fact:aml.dossier:CR84920:discrepancy_multiplier}}"


def runtime(steps, knowledge=None):
    llm = ScriptedLlm(steps=steps)
    models = replace(ReadModels.default(), knowledge=knowledge)
    rt = AssistantRuntime(
        port=build_port(models), settings=ON, session_service=build_session_service(ON), model=llm
    )
    return rt, llm


def turn(rt, question, principal=AML, entity="CR84920"):
    return asyncio.run(rt.run_turn(principal=principal, question=question, entity_id=entity))


def test_the_entity_on_screen_has_its_dossier_before_the_model_speaks() -> None:
    rt, llm = runtime([draft(f"The discrepancy is {FIGURE}.")])
    out = turn(rt, "What is the discrepancy?")
    assert out.status == "ok" and "16x" in out.answer.text
    assert out.model_calls == 1 and len(llm.seen) == 1  # no model call was spent choosing the tool
    assert out.steps == ("get_aml_dossier",)
    first = llm.seen[0].contents
    names = [p.function_call.name for c in first for p in c.parts or [] if p.function_call]
    assert names == ["get_aml_dossier"]
    assert any(p.function_response for c in first for p in c.parts or [])
    assert [f.fact_id for f in out.answer.figures] == ["aml.dossier:CR84920:discrepancy_multiplier"]


def test_the_model_may_still_call_other_tools_after_the_prefetched_one() -> None:
    rt, llm = runtime(
        [call("get_activity_timeline", entity_id="CR84920"), draft(f"It is {FIGURE}.")]
    )
    out = turn(rt, "What happened on this account and what is the discrepancy?")
    assert out.steps == ("get_aml_dossier", "get_activity_timeline")
    assert out.model_calls == 2


def test_a_regulation_question_is_searched_first_and_quoted_in_one_model_call() -> None:
    rt, llm = runtime(
        [draft(f"The guidance sets a period.\n\n{{{{quote:{FILING.passage_id}#s1}}}}")],
        knowledge=StaticIndex(ALL),
    )
    out = turn(
        rt, "When must a suspicious transaction report be filed under the regulation?", entity=None
    )
    assert out.model_calls == 1 and out.steps == ("search_regulations",)
    assert [s.passage_id for s in out.answer.sources] == [FILING.passage_id]


def test_a_retried_draft_keeps_the_prefetched_result_and_does_not_run_the_tool_again() -> None:
    rt, llm = runtime([draft("The discrepancy is 17x."), draft(f"It is {FIGURE}.")])
    out = turn(rt, "What is the discrepancy?")
    assert out.answer.attempts == 2 and out.steps == ("get_aml_dossier",)
    assert out.model_calls == 2


def test_a_tool_that_fails_is_reported_to_the_model_not_hidden() -> None:
    rt, _ = runtime([draft("No dossier is available for that account.")])
    out = turn(rt, "What is the discrepancy?", entity="CR99999")
    assert out.steps == ("get_aml_dossier",)
    assert out.tool_calls[0].error_code is not None


def test_the_plan_is_small_and_conservative() -> None:
    assert plan(
        Workstation.AML_INVESTIGATOR, "Draft the SAR narrative for CR84920.", "CR84920"
    ) == [("get_aml_dossier", {"entity_id": "CR84920"})]
    assert (
        plan(
            Workstation.AML_INVESTIGATOR,
            "What does the Maltese FIAU say about record keeping?",
            None,
        )[0][1]["jurisdiction"]
        == "MT"
    )
    assert plan(Workstation.PARTNER_MANAGER, "Why is this partner at risk?", "PTR-882") == [
        ("get_partner_signals", {"entity_id": "PTR-882"})
    ]
    assert plan(Workstation.EXECUTIVE, "Give me the morning briefing.", None) == [
        ("get_briefing", {})
    ]
    assert plan(Workstation.EXECUTIVE, "What is our net revenue?", None) == []
    assert (
        plan(Workstation.DATA_OPERATIONS, "What is the regulation on data quality?", None) == []
    )  # that workstation has no such tool
    assert plan(Workstation.AML_INVESTIGATOR, "hello", None) == []


def test_a_tool_the_workstation_is_not_offered_is_never_run() -> None:
    rt, llm = runtime([draft("I cannot answer that.")])
    out = turn(
        rt,
        "What does the regulation say about retention?",
        principal=principal_for("bob", "partner_manager"),
        entity=None,
    )
    assert "search_regulations" not in out.steps
