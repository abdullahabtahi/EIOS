"""The geospatial assistant end to end with a scripted model: map-aware prefetch, map commands, instructions."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from typing import Any

import pytest

from eios.assistant.assembly import FAIL_CLOSED_TEXT
from eios.assistant.config import AssistantSettings
from eios.assistant.geo_context import GEO_RULES, MapContext, describe_map, geo_steps
from eios.assistant.origin_guard import REFUSAL
from eios.assistant.runtime import AssistantRuntime, TurnOutcome
from eios.assistant.scripted_model import ScriptedLlm, Step, call, draft
from eios.assistant.sessions import build_session_service
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from tests.ontology.port.conftest import seeded_geo

GEO = principal_for("alice", "geospatial")
EXIT = {"view": "logins", "selection": {"kind": "gateway", "id": "GW-NG-X00"}}
FLAGGED = "{{fact:geo.exit:GW-NG-X00:flagged_accounts}}"


def _runtime(steps: list[Step], prefetch: bool = True) -> tuple[AssistantRuntime, ScriptedLlm]:
    settings = AssistantSettings.from_env(
        {
            "EIOS_ENVIRONMENT": "test",
            "EIOS_ASSISTANT_TURN_DEADLINE_S": "20",
            "EIOS_ASSISTANT_PREFETCH": "1" if prefetch else "0",
        }
    )
    llm = ScriptedLlm(steps=steps)
    runtime = AssistantRuntime(
        port=build_port(replace(ReadModels.default(), geo=seeded_geo())),
        settings=settings,
        session_service=build_session_service(settings),
        model=llm,
    )
    return runtime, llm


def _turn(
    runtime: AssistantRuntime,
    question: str,
    context: dict[str, Any] | None = EXIT,
    principal: Any = GEO,
) -> TurnOutcome:
    return asyncio.run(
        runtime.run_turn(principal=principal, question=question, entity_context=context)
    )


def test_the_selected_exit_is_read_before_the_model_speaks_and_the_map_moves_to_it() -> None:
    runtime, llm = _runtime(
        [draft(f"This exit {{{{map:gateway:GW-NG-X00}}}} is used by {FLAGGED} flagged accounts.")]
    )
    out = _turn(runtime, "Why is this exit suspicious?")
    assert out.status == "ok" and out.answer.attempts == 1
    assert out.steps == ("get_shared_exit",)  # prefetched from the map's selection
    assert out.model_calls == 1  # one model call: the draft
    assert out.answer.view_commands == ({"kind": "gateway", "id": "GW-NG-X00"},)
    assert "{{" not in out.answer.text and out.answer.text.startswith("This exit is used by")
    assert [f.fact_id for f in out.answer.figures] == ["geo.exit:GW-NG-X00:flagged_accounts"]
    instruction = str(llm.seen[0].config.system_instruction)
    assert "Geography is evidence, never a verdict" in instruction
    assert "with gateway GW-NG-X00 selected" in instruction


def test_a_map_move_to_something_no_tool_returned_is_sent_back() -> None:
    runtime, llm = _runtime(
        [
            draft("Look at the exit in Iraq {{map:gateway:GW-IQ-X02}}."),
            draft("The exit in Nigeria {{map:gateway:GW-NG-X00}} is the one selected."),
        ]
    )
    out = _turn(runtime, "Where else should I look?")
    assert out.answer.attempts == 2
    assert out.answer.view_commands == ({"kind": "gateway", "id": "GW-NG-X00"},)
    assert "not returned by a tool in this turn" in str(llm.seen[-1].config.system_instruction)


def test_two_bad_map_moves_fail_closed_with_no_move() -> None:
    bad = draft("Look at {{map:account:CR99999}}.")
    runtime, _ = _runtime([bad, bad])
    out = _turn(runtime, "Who else?")
    assert out.answer.text.startswith(FAIL_CLOSED_TEXT) and out.answer.view_commands == ()


def test_nothing_selected_reads_the_overview_and_a_named_account_wins() -> None:
    runtime, _ = _runtime([draft("Start with the shared exits.")])
    out = _turn(runtime, "Where should I look first?", {"view": "corridors"})
    assert out.steps == ("get_geo_overview",)
    runtime, _ = _runtime([draft("CR11568 logs in through a shared exit.")])
    out = _turn(runtime, "Tell me about CR11568", EXIT)
    assert out.steps == ("get_geo_account",)


def test_a_list_change_question_runs_the_list_comparison() -> None:
    runtime, _ = _runtime([draft("The June plenary added two countries.")])
    out = _turn(runtime, "What did the June FATF plenary change for us?", {"view": "jurisdictions"})
    assert out.steps == ("get_list_change_impact",)
    assert out.tool_calls[0].arguments == {"list_id": "fatf"}


@pytest.mark.parametrize(
    "question",
    [
        "Which nationality launders the most money in our book?",
        "Are clients of some religion riskier?",
    ],
)
def test_a_question_about_people_by_origin_is_refused_with_no_tool_and_no_model_call(
    question: str,
) -> None:
    # The scripted model would call a tool; the guard answers before it is ever asked.
    runtime, llm = _runtime([call("get_geo_overview"), draft("Nigeria.")])
    out = _turn(runtime, question, {"view": "corridors"})
    assert out.answer.text == REFUSAL and out.answer.figures == ()
    assert out.tool_calls == () and out.model_calls == 0 and llm.seen == []


def test_another_workstation_can_never_move_the_map() -> None:
    aml = principal_for("alice", "aml_investigator")
    runtime, _ = _runtime(
        [
            call("get_aml_dossier", entity_id="CR84920"),
            draft("See {{map:account:CR84920}}."),
            draft("Done."),
        ],
        prefetch=False,
    )
    out = asyncio.run(runtime.run_turn(principal=aml, question="Show it", entity_id="CR84920"))
    assert out.answer.view_commands == ()
    assert out.answer.attempts == 2


@pytest.mark.parametrize(
    ("question", "named", "context", "expected"),
    [
        ("Why is this suspicious?", None, EXIT, [("get_shared_exit", {"gateway_id": "GW-NG-X00"})]),
        (
            "How big is this corridor?",
            None,
            {"view": "corridors", "selection": {"kind": "corridor", "id": "ID>MM"}},
            [("get_corridor", {"corridor_id": "ID>MM"})],
        ),
        (
            "Brief me",
            None,
            {"view": "jurisdictions", "selection": {"kind": "country", "id": "IQ"}},
            [("get_jurisdiction", {"country_id": "IQ"})],
        ),
        (
            "Who are these?",
            None,
            {"view": "logins", "selection": {"kind": "mismatch", "id": "TH>NG"}},
            [],
        ),
        ("Anything new?", None, None, [("get_geo_overview", {})]),
        (
            "Which accounts did the EU delisting touch?",
            None,
            None,
            [("get_list_change_impact", {"list_id": "eu"})],
        ),
        (
            "Since the EU took Nigeria off its high-risk list, what continues?",
            None,
            None,
            [("get_list_change_impact", {"list_id": "eu"})],
        ),
        (
            "Is CR11568 part of a ring?",
            "CR11568",
            EXIT,
            [("get_geo_account", {"entity_id": "CR11568"})],
        ),
        ("Who uses gw-iq-x02?", None, EXIT, [("get_shared_exit", {"gateway_id": "GW-IQ-X02"})]),
        ("How much moves on ID>MM?", None, None, [("get_corridor", {"corridor_id": "ID>MM"})]),
        (
            "What is our exposure to Iraq (IQ)?",
            None,
            None,
            [("get_jurisdiction", {"country_id": "IQ"})],
        ),
        ("Which nationality launders the most money?", None, None, []),  # nothing read ahead for it
        (
            "Rank the top corridors by risk for me.",
            None,
            None,
            [("list_geo_leads", {"kind": "corridor"})],
        ),
        (
            "What are the riskiest shared exits?",
            None,
            None,
            [("list_geo_leads", {"kind": "shared_exit"})],
        ),
        ("Top accounts, please", None, None, [("list_geo_leads", {"kind": "account"})]),
        ("Rank accounts by ethnicity", None, None, []),  # refused, so nothing is read for it
        ("Where should I look first?", None, None, [("get_geo_overview", {})]),
    ],
)
def test_the_prefetch_plan_follows_the_question_then_the_map(
    question: str, named: str | None, context: dict[str, Any] | None, expected: list[Any]
) -> None:
    assert geo_steps(question, named, context) == expected


def test_the_map_context_is_validated_and_described_plainly() -> None:
    assert "nothing selected" in describe_map({"view": "corridors"})
    text = describe_map(
        {"view": "jurisdictions", "basis": "eu", "selection": {"kind": "country", "id": "NG"}}
    )
    assert "coloured by the EU high-risk list" in text and "country NG selected" in text
    assert describe_map({"view": "satellite"}) == "The map context is not known."
    with pytest.raises(ValueError):
        MapContext.model_validate(
            {"view": "logins", "selection": {"kind": "gateway", "id": "x;drop"}}
        )
    assert "not assessed" in GEO_RULES
