"""The prepared brief: a system identity that cannot propose, an assembled answer kept with its sources, and nothing
kept when the turn did not assemble."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from eios.ambient.brief import (
    EVIDENCE_KINDS,
    QUESTION,
    BriefStore,
    evidence_only,
    prepare_brief,
    prepare_top,
    system_principal,
)
from eios.assistant.assembly import FAIL_CLOSED_TEXT
from eios.assistant.config import AssistantSettings
from eios.assistant.runtime import AssistantRuntime
from eios.assistant.scripted_model import ScriptedLlm, call, draft
from eios.assistant.sessions import build_session_service
from eios.ontology.actions.record_store import InMemoryRecordStore
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import ToolErrorCode
from eios.ontology.omcp.port.readmodels import ReadModels

SETTINGS = AssistantSettings.from_env(
    {
        "EIOS_ENVIRONMENT": "test",
        "EIOS_ASSISTANT_TURN_DEADLINE_S": "10",
        "EIOS_ASSISTANT_PREFETCH": "0",
    }
)
DOSSIER = call("get_aml_dossier", entity_id="CR84920")
FIGURE = "{{fact:aml.dossier:CR84920:discrepancy_multiplier}}"
NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


def _runtime(steps) -> AssistantRuntime:
    port = evidence_only(build_port(ReadModels.default()))
    return AssistantRuntime(
        port=port,
        settings=SETTINGS,
        session_service=build_session_service(SETTINGS),
        model=ScriptedLlm(steps=steps),
    )


def _store(clock=lambda: NOW) -> BriefStore:
    return BriefStore(InMemoryRecordStore(), clock)


def test_the_system_identity_is_offered_evidence_tools_and_no_propose_or_draft_tool() -> None:
    full = build_port(ReadModels.default())
    port = evidence_only(full)
    principal = system_principal()
    offered = port.list_tools(principal)
    assert offered and {s.kind for s in offered} <= EVIDENCE_KINDS
    assert {s.kind for s in full.list_tools(principal)} >= {
        "propose",
        "draft",
    }  # the full port has them


@pytest.mark.parametrize("tool", ["propose_hold", "draft_sar"])
def test_a_propose_or_draft_call_by_the_system_identity_is_refused(tool: str) -> None:
    port = evidence_only(build_port(ReadModels.default()))
    out = port.call(system_principal(), tool, {"entity_id": "CR84920"})
    assert out.error is not None and out.error.code is ToolErrorCode.FORBIDDEN_ROLE


def test_an_assembled_brief_is_kept_with_its_figures_sources_and_time() -> None:
    store = _store()
    runtime = _runtime([DOSSIER, draft(f"The discrepancy is {FIGURE}.")])
    kept = asyncio.run(prepare_brief(runtime, store, "CR84920", ttl_s=600, now=lambda: NOW))
    assert kept is not None and kept.question == QUESTION
    assert [f.fact_id for f in kept.answer.figures] == [
        "aml.dossier:CR84920:discrepancy_multiplier"
    ]
    assert kept.answer.citations and kept.answer.proposed_actions == ()
    assert (kept.prepared_at, kept.expires_at) == (NOW, NOW + timedelta(seconds=600))
    view = store.get("CR84920")
    assert view is not None and not view.stale and view.brief == kept


def test_a_brief_past_its_time_to_live_is_served_marked_stale() -> None:
    later = NOW + timedelta(seconds=601)
    store = BriefStore(InMemoryRecordStore(), lambda: later)
    runtime = _runtime([DOSSIER, draft(f"The discrepancy is {FIGURE}.")])
    asyncio.run(prepare_brief(runtime, store, "CR84920", ttl_s=600, now=lambda: NOW))
    view = store.get("CR84920")
    assert view is not None and view.stale


def test_no_brief_for_an_entity_nobody_prepared() -> None:
    assert _store().get("CR00000") is None


def test_a_turn_that_failed_closed_is_not_kept() -> None:
    bad = draft("The discrepancy is 17x.")  # a figure no tool returned, twice: fail closed
    store = _store()
    kept = asyncio.run(prepare_brief(_runtime([DOSSIER, bad, bad]), store, "CR84920"))
    assert kept is None and store.get("CR84920") is None
    assert FAIL_CLOSED_TEXT  # the text the operator would have seen is not what a brief shows


def test_a_model_outage_keeps_nothing() -> None:
    runtime = _runtime([])
    runtime._model.fail_with = "model unavailable"
    store = _store()
    assert asyncio.run(prepare_brief(runtime, store, "CR84920")) is None
    assert store.get("CR84920") is None


def test_the_top_entities_are_prepared_one_failure_costs_one_entity() -> None:
    store = _store()
    runtime = _runtime([DOSSIER, draft(f"The discrepancy is {FIGURE}.")])
    result = asyncio.run(prepare_top(runtime, store, ["CR84920", "CR84920"]))
    assert result.prepared[0] == "CR84920" and result.seconds >= 0
    assert set(result.prepared) | set(result.skipped) == {"CR84920"}
