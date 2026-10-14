"""PortTool: ADK sees only the verified role's tools, every call goes through the governed port (spec 021 FR-006, FR-009)."""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from eios.assistant.tools import FACTS_KEY, IDENTIFIERS_KEY, PROPOSALS_KEY, build_toolset
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
        assert [
            {k: v for k, v in p.items() if k != "stage_request"} for p in ctx.state[PROPOSALS_KEY]
        ] == [payload]
        assert "stage_request" not in payload  # the model never sees hub vocabulary


def test_a_list_result_names_one_fact_per_item_and_each_can_be_shown(
    port: GovernedToolPort,
) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    ctx = _context()
    payload = _run(tools["get_activity_timeline"], {"entity_id": "CR84920"}, ctx)
    ids = payload["fact_ids"]
    assert "events[].event_amount_usd" not in ids
    with_amount = [i for i, e in enumerate(payload["events"]) if e["event_amount_usd"] is not None]
    assert with_amount, "the fixture has at least one event with an amount"
    first = with_amount[0]
    fact_id = f"aml.timeline:CR84920:events[{first}].event_amount_usd"
    assert ids[f"events[{first}].event_amount_usd"] == fact_id
    assert ctx.state[FACTS_KEY][fact_id]["value"] == payload["events"][first]["event_amount_usd"]
    assert ctx.state[FACTS_KEY][fact_id]["unit"] == "USD"
    assert not any(
        f"events[{i}]" in key
        for i in range(len(payload["events"]))
        if i not in with_amount
        for key in ids
    )


def test_a_long_list_is_bounded_so_it_cannot_flood_the_model() -> None:
    from eios.assistant.tools import MAX_LIST_ITEMS, expand_fact_ids

    payload = {
        "rows": [{"amount": float(i)} for i in range(MAX_LIST_ITEMS + 25)],
        "fact_ids": {"rows[].amount": "cap:E1:rows[].amount"},
        "units": {"rows[].amount": "USD"},
    }
    assert len(expand_fact_ids(payload)["fact_ids"]) == MAX_LIST_ITEMS


def test_identifiers_a_result_returned_are_remembered_for_the_assembler(
    port: GovernedToolPort,
) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    ctx = _context()
    _run(tools["draft_sar"], {"entity_id": "CR84920"}, ctx)
    ids = set(ctx.state[IDENTIFIERS_KEY])
    assert {"case_aml_84920", "sar_20261014_CR84920"} <= ids
    assert not any(" " in i for i in ids)  # prose such as the narrative is never an identifier


def test_text_marked_untrusted_never_contributes_an_identifier(port: GovernedToolPort) -> None:
    from eios.assistant.tools import identifiers_of

    payload = {"untrusted": True, "case_id": "case_evil_99999", "source": "x"}
    assert identifiers_of(payload) == set()
    assert identifiers_of({"untrusted": False, "case_id": "case_ok_12345"}) == {"case_ok_12345"}
    assert identifiers_of({"narrative_summary": "case_x_12345 is here", "note_id": "a b"}) == set()


def test_every_capability_tells_the_model_what_it_is_for() -> None:
    from eios.ontology.omcp.port.catalogue import all_specs
    from eios.ontology.omcp.port.descriptions import DESCRIPTIONS

    specs = all_specs()
    assert all(s.description for s in specs), [s.capability for s in specs if not s.description]
    assert set(DESCRIPTIONS) == {s.capability for s in specs}  # none stale, none missing


def test_a_description_carries_no_number_for_the_model_to_copy() -> None:
    from eios.ontology.omcp.port.descriptions import DESCRIPTIONS

    for capability, text in DESCRIPTIONS.items():
        assert not any(ch.isdigit() for ch in text), capability


def test_the_sar_tool_says_the_dossier_comes_first() -> None:
    from eios.ontology.omcp.port.descriptions import DESCRIPTIONS

    assert "get_aml_dossier" in DESCRIPTIONS["aml.sar_draft"]


def test_a_proposal_reference_is_a_name_the_operator_may_be_told() -> None:
    from eios.assistant.tools import identifiers_of

    assert identifiers_of({"proposal_ref": "prop-23f928c1d5"}) == {"prop-23f928c1d5"}


def test_a_hold_proposal_carries_the_exact_request_a_human_stages(port: GovernedToolPort) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "aml_investigator"))}
    ctx = _context()
    _run(tools["propose_hold"], {"entity_id": "CR84920"}, ctx)
    request = ctx.state[PROPOSALS_KEY][0]["stage_request"]
    assert request["action_type"] == "HoldWithdrawal"
    assert request["target_entity_id"] == "CR84920"
    assert request["requires_four_eyes"] is True
    assert request["metadata"]["txn_id"] == "W-84920-1"  # the withdrawal, not the account id
    assert request["metadata"]["reason"]


def test_a_retention_proposal_carries_the_playbook_and_budget(port: GovernedToolPort) -> None:
    tools = {t.name: t for t in build_toolset(port, principal_for("op-1", "partner_manager"))}
    ctx = _context()
    _run(
        tools["propose_partner_action"],
        {"entity_id": "PTR-882", "playbook_id": "pb_master_tier_upgrade"},
        ctx,
    )
    request = ctx.state[PROPOSALS_KEY][0]["stage_request"]
    assert request["action_type"] == "LaunchRetentionPlaybook"
    assert request["metadata"] == {
        "partner_ids": ["PTR-882"],
        "playbook_id": "pb_master_tier_upgrade",
        "budget": 4500.0,
    }
    assert request["requires_four_eyes"] is True  # this deal is over the fast-path budget


def test_names_a_trusted_result_returned_are_not_figures_even_with_digits_in_them() -> None:
    from eios.assistant.tools import identifiers_of

    payload = {
        "untrusted": False,
        "partners": [
            {"partner_id": "PTR-339", "name": "Medellin P2P Payment Ring"},
            {"partner_id": "PTR-520", "primary_root_cause": "Rebate Dispute on Volatility 100"},
        ],
    }
    found = identifiers_of(payload)
    assert {"Medellin P2P Payment Ring", "PTR-339", "PTR-520"} <= found
    assert "Rebate Dispute on Volatility 100" in found
    assert "Volatility 100" in found  # the product name on its own, as a model would write it
    assert "P2P" in found
    assert "100" not in found and "2" not in found  # a bare number is never a name


def test_a_result_marked_untrusted_names_nothing_and_narrative_fields_are_not_names() -> None:
    from eios.assistant.tools import identifiers_of

    assert identifiers_of({"untrusted": True, "name": "Evil 99 Corp"}) == set()
    assert identifiers_of({"summary": "Revenue up 18 percent", "name": "x" * 200}) == set()
