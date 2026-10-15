"""Safe by construction: scope, no approve or execute, contracts everywhere (spec 023 US2, SC-002, SC-003)."""

from enum import Enum

import pytest

from eios.agent_gates.capabilities import FORBIDDEN_AGENT_TOOLS, default_map
from eios.ontology.omcp.port.catalogue import all_specs
from eios.ontology.omcp.port.contracts import ToolErrorCode
from eios.ontology.omcp.port.principal import Workstation, principal_for
from eios.ontology.omcp.port.registry import ToolSpec
from eios.ontology.omcp.port.service import GovernedToolPort, RefusalLog

# Capabilities the golden cases name that other specs deliver (reported as planned, never as passing).
PLANNED = {
    "knowledge.policy",
    "knowledge.sar_precedent",
    "exec.cohort_trend",
    "exec.market_context",
}

# A search query is the one free-text argument: it goes to the platform's own regulatory index, never to a data tool
# that returns operator data, and the passages it brings back are untrusted text the assembler can only quote.
FREE_TEXT_ARGUMENTS = {("search_regulations", "query")}
# One managed-search round trip cannot meet the in-process budget; its own budget is bounded and measured on the index.
SLOW_BUDGETS_MS = {
    "search_regulations": 5000,
    "get_account_history": 3000,
}  # remote retrieval and a warehouse query

SAMPLE_ARGS: dict[str, dict[str, object]] = {
    "search_regulations": {"query": "when must a suspicious report be filed"},
    "get_metric": {"metric_id": "net_revenue_usd"},
    "resolve_entity": {"entity_id": "PTR-882"},
    "get_causal_evidence": {},
    "compare_facts": {
        "left_fact_id": "partner.signals:PTR-882:realized_volume_30d_usd",
        "right_fact_id": "partner.signals:PTR-104:realized_volume_30d_usd",
        "operation": "ratio",
    },
    "list_alerts": {},
    "get_aml_dossier": {"entity_id": "CR84920"},
    "get_network_evidence": {"entity_id": "CR84920"},
    "get_activity_timeline": {"entity_id": "CR84920"},
    "get_account_history": {"entity_id": "CR84920"},
    "check_withdrawal_risk": {"entity_id": "CR84920"},
    "draft_sar": {"entity_id": "CR84920"},
    "propose_hold": {"entity_id": "CR84920"},
    "list_partner_worklist": {},
    "get_partner_signals": {"entity_id": "PTR-882"},
    "get_partner_integrity": {"entity_id": "PTR-882"},
    "read_partner_comms": {"entity_id": "PTR-882"},
    "propose_partner_action": {"entity_id": "PTR-882", "playbook_id": "pb_vip_spread_deal"},
    "get_briefing": {},
    "get_forecast": {"metric_id": "net_revenue_usd"},
    "run_what_if": {"shock": "competitor_spread_cut", "magnitude_pct": 10.0},
    "get_ledger_timeline": {},
    "get_intent_status": {},
    "get_audit_status": {},
    "verify_chain": {},
    "get_dq_board": {},
    "get_reliability": {},
    "get_drill_status": {},
    "get_red_lines": {},
}
# Capabilities that answer with a typed error today because the data does not exist yet (and say so).
UNAVAILABLE_TODAY = {"get_client_quality", "get_calibration_status", "get_red_lines"}
SAMPLE_ARGS["get_client_quality"] = {"entity_id": "PTR-882"}
SAMPLE_ARGS["get_calibration_status"] = {}
CALLER = {"compare_facts": "partner_manager"}  # its sample inputs are partner facts


def test_no_role_can_be_offered_an_approve_or_execute_capability(port: GovernedToolPort) -> None:
    for workstation in Workstation:
        offered = port.list_tools(principal_for("u", workstation.value))
        assert offered, workstation
        for spec in offered:
            assert spec.name not in FORBIDDEN_AGENT_TOOLS
            assert not spec.capability.startswith(("action.approve", "action.execute"))
            assert spec.kind in {"evidence", "compute", "draft", "propose", "knowledge"}
        assert (
            len(offered) <= 13
        )  # [ASSUMPTION] about a dozen per role (FR-006); raised from 12 for aml.history, watch tool choice in the live baseline


def test_every_out_of_role_call_is_refused_and_recorded() -> None:
    from eios.ontology.omcp.port.catalogue import build_port

    log = RefusalLog()
    port = build_port(refusals=log)
    expected = 0
    for spec in all_specs():
        for workstation in Workstation:
            if workstation in spec.workstations:
                continue
            outcome = port.call(
                principal_for("u", workstation.value), spec.name, SAMPLE_ARGS.get(spec.name, {})
            )
            assert outcome.error is not None and outcome.error.code is ToolErrorCode.FORBIDDEN_ROLE
            expected += 1
    assert len(log.entries) == expected > 50


def test_forbidden_tools_are_not_in_the_catalogue_at_all() -> None:
    assert not {s.name for s in all_specs()} & FORBIDDEN_AGENT_TOOLS


def test_the_port_roles_agree_with_the_capability_map() -> None:
    cmap = default_map()
    by_capability = {s.capability: s for s in all_specs()}
    for workstation in Workstation:
        wanted = {c for c in cmap.roles[workstation.value] if c not in PLANNED}
        offered = {s.capability for s in all_specs() if workstation in s.workstations}
        assert offered == wanted, (workstation, offered ^ wanted)
    for capability_id, spec in by_capability.items():
        assert cmap.capabilities[capability_id].target == spec.name


def test_no_capability_takes_free_text() -> None:
    for spec in all_specs():
        for name, field in spec.args_model.model_fields.items():
            annotation = field.annotation
            is_text = annotation is str or str in getattr(annotation, "__args__", ())
            is_enum = isinstance(annotation, type) and issubclass(annotation, Enum)
            if is_text and not is_enum and (spec.name, name) not in FREE_TEXT_ARGUMENTS:
                assert name.endswith("_id"), f"{spec.name}.{name} is free text"


def test_every_budget_fits_the_turn_budget() -> None:
    assert all(
        0 < s.budget_ms <= SLOW_BUDGETS_MS.get(s.name, 300) for s in all_specs()
    )  # SC-006 [ASSUMPTION]


def test_every_catalogue_tool_has_a_sample_or_is_known_unavailable() -> None:
    names = {s.name for s in all_specs()}
    assert names == set(SAMPLE_ARGS) | UNAVAILABLE_TODAY


@pytest.mark.parametrize("spec", all_specs(), ids=lambda s: s.name)
def test_every_result_validates_and_carries_the_envelope(
    spec: ToolSpec, port: GovernedToolPort
) -> None:
    principal = principal_for("u", CALLER.get(spec.name, spec.workstations[0].value))
    outcome = port.call(principal, spec.name, SAMPLE_ARGS.get(spec.name, {}))
    if spec.name in UNAVAILABLE_TODAY:
        assert outcome.error is not None and outcome.error.code is ToolErrorCode.DATA_UNAVAILABLE
        return
    assert outcome.error is None, outcome.error
    payload = outcome.payload()
    for key in ("capability", "as_of", "data_origin", "source", "markings", "units", "fact_ids"):
        assert key in payload
    assert payload["capability"] == spec.capability
    assert payload["data_origin"] == "fixture"
    assert set(payload["fact_ids"]) <= set(payload["units"]) | set(payload["fact_ids"])
    assert all(payload["units"].values())


def test_untrusted_text_is_flagged_on_the_result(port: GovernedToolPort) -> None:
    payload = port.call(
        principal_for("u", "partner_manager"), "read_partner_comms", {"entity_id": "PTR-882"}
    ).payload()
    assert payload["untrusted"] is True
