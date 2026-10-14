"""PortTool: ADK sees only the verified role's tools, every call goes through the governed port (spec 021 FR-006, FR-009)."""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from eios.assistant.tools import FACTS_KEY, PROPOSALS_KEY, build_toolset
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import Workstation, principal_for
from eios.ontology.omcp.port.service import GovernedToolPort

FORBIDDEN_PREFIXES = ("action.approve", "action.execute", "approve", "execute")


@pytest.fixture(scope="module")
def port() -> GovernedToolPort:
    return build_port()


def _context() -> Any:
    return SimpleNamespace(state={})


def _run(tool: Any, args: dict[str, Any], ctx: Any) -> dict[str, Any]:
    return asyncio.run(tool.run_async(args=args, tool_context=ctx))


def test_each_workstation_is_offered_exactly_its_port_toolset(port: GovernedToolPort) -> None:
    for ws in Workstation:
        principal = principal_for("op-1", ws.value)
        offered = {t.name for t in build_toolset(port, principal)}
        assert offered == {s.name for s in port.list_tools(principal)}
        assert offered, ws


def test_every_declaration_builds_with_a_json_schema(port: GovernedToolPort) -> None:
    for ws in Workstation:
        for tool in build_toolset(port, principal_for("op-1", ws.value)):
            declaration = tool._get_declaration()
            assert declaration is not None
            assert declaration.name == tool.name
            assert declaration.parameters_json_schema is not None
            assert declaration.description


def test_no_workstation_is_offered_approve_or_execute(port: GovernedToolPort) -> None:
    for ws in Workstation:
        for tool in build_toolset(port, principal_for("op-1", ws.value)):
            assert not tool.name.startswith(FORBIDDEN_PREFIXES), tool.name


def test_a_successful_call_returns_the_payload_and_remembers_its_fact_ids(
    port: GovernedToolPort,
) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    ctx = _context()
    payload = _run(tools["get_aml_dossier"], {"entity_id": "CR84920"}, ctx)
    assert "error" not in payload
    assert payload["fact_ids"]
    facts = ctx.state[FACTS_KEY]
    assert facts["aml.dossier:CR84920:discrepancy_multiplier"]["value"] == 16.0
    assert facts["aml.dossier:CR84920:discrepancy_multiplier"]["unit"] == "multiplier"


def test_an_unknown_entity_is_a_typed_error_and_offers_no_fact_ids(port: GovernedToolPort) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    ctx = _context()
    payload = _run(tools["get_aml_dossier"], {"entity_id": "CR-NOPE"}, ctx)
    assert payload["error"]["code"] == "NOT_FOUND"
    assert not ctx.state.get(FACTS_KEY)


def test_arguments_cannot_carry_an_identity(port: GovernedToolPort) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    payload = _run(
        tools["get_aml_dossier"], {"entity_id": "CR84920", "uid": "someone-else"}, _context()
    )
    assert payload["error"]["code"] == "INVALID_ARGUMENTS"


def test_the_facts_of_two_calls_accumulate_in_one_turn(port: GovernedToolPort) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    ctx = _context()
    _run(tools["get_aml_dossier"], {"entity_id": "CR84920"}, ctx)
    first = set(ctx.state[FACTS_KEY])
    _run(tools["list_alerts"], {}, ctx)
    assert first <= set(ctx.state[FACTS_KEY])


def test_a_proposal_is_kept_for_the_answer_and_stages_nothing(port: GovernedToolPort) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    ctx = _context()
    payload = _run(tools["propose_hold"], {"entity_id": "CR84920"}, ctx)
    if "error" in payload:  # an unproposable entity is a typed refusal, never a record
        assert not ctx.state.get(PROPOSALS_KEY)
    else:
        assert ctx.state[PROPOSALS_KEY] == [payload]
