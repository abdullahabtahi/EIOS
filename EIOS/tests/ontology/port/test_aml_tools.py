"""AML capabilities: the figures are the workstation's figures (spec 023 US1)."""

import pytest

from eios.cockpit.aml import AMLWorkstationService
from eios.ontology.omcp.port.contracts import DataOrigin, ToolErrorCode
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.ontology.port.conftest import who

AML = who("aml_investigator")


def _ok(port: GovernedToolPort, tool: str, args: dict[str, object]) -> dict[str, object]:
    outcome = port.call(AML, tool, args)
    assert outcome.error is None, outcome.error
    return outcome.payload()


def test_dossier_matches_the_workstation_payload(port: GovernedToolPort) -> None:
    screen = AMLWorkstationService().get_entity_dossier("CR84920").to_contract_dict()
    got = _ok(port, "get_aml_dossier", {"entity_id": "cr84920"})
    assert got["entity_id"] == "CR84920"
    assert got["discrepancy_multiplier"] == screen["discrepancy"]["discrepancy_multiplier"] == 16.0
    assert got["composite_risk_score"] == screen["composite_risk_score"]
    assert got["declared_monthly_income_usd"] == screen["kyc"]["declared_monthly_income_usd"]
    assert got["realized_deposit_volume_30d_usd"] == 8000.0
    assert got["syndicate_ring_size"] == screen["syndicate_ring_size"]


def test_every_figure_has_unit_origin_source_marking_and_id(port: GovernedToolPort) -> None:
    got = _ok(port, "get_aml_dossier", {"entity_id": "CR84920"})
    assert got["units"]["discrepancy_multiplier"] == "multiplier"
    assert got["units"]["declared_monthly_income_usd"] == "USD"
    assert got["data_origin"] == DataOrigin.FIXTURE.value
    assert got["source"] and got["as_of"]
    assert set(got["markings"]) == {"PII", "SENSITIVE_COMPLIANCE"}
    assert got["fact_ids"]["discrepancy_multiplier"] == "aml.dossier:CR84920:discrepancy_multiplier"


@pytest.mark.parametrize(
    "tool",
    [
        "get_aml_dossier",
        "get_network_evidence",
        "get_activity_timeline",
        "check_withdrawal_risk",
        "draft_sar",
    ],
)
def test_unknown_account_is_not_found_for_every_tool(port: GovernedToolPort, tool: str) -> None:
    outcome = port.call(AML, tool, {"entity_id": "CR00000"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.NOT_FOUND


@pytest.mark.parametrize(
    "tool", ["get_aml_dossier", "get_network_evidence", "get_activity_timeline", "draft_sar"]
)
def test_a_known_account_without_a_dossier_is_unavailable_not_a_neighbour(
    port: GovernedToolPort, tool: str
) -> None:
    outcome = port.call(AML, tool, {"entity_id": "CR73491"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.DATA_UNAVAILABLE


def test_a_partner_id_is_not_an_account(port: GovernedToolPort) -> None:
    outcome = port.call(AML, "get_aml_dossier", {"entity_id": "PTR-882"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.NOT_FOUND


def test_alerts_are_ranked_and_filtered(port: GovernedToolPort) -> None:
    got = _ok(port, "list_alerts", {"min_score": 70, "limit": 5})
    scores = [a["risk_score"] for a in got["alerts"]]
    assert scores == sorted(scores, reverse=True) and min(scores) >= 70
    assert got["units"]["alerts[].risk_score"] == "score"


def test_network_flags_hub_suppression(port: GovernedToolPort) -> None:
    got = _ok(port, "get_network_evidence", {"entity_id": "CR84920"})
    suppressed = [n for n in got["nodes"] if n["is_hub_suppressed"]]
    assert suppressed and got["hub_suppressed_count"] == len(suppressed)
    assert all(n["degree"] > 100 for n in suppressed if n["node_type"] == "PAYMENT_AGENT")


def test_timeline_is_time_ordered_and_totals_the_dossier(port: GovernedToolPort) -> None:
    got = _ok(port, "get_activity_timeline", {"entity_id": "CR84920"})
    times = [e["at"] for e in got["events"]]
    assert times == sorted(times)
    deposits = sum(e["amount_usd"] for e in got["events"] if e["kind"] == "DEPOSIT")
    assert deposits == 8000.0


def test_withdrawal_risk_is_a_read_and_stages_nothing(port: GovernedToolPort) -> None:
    got = _ok(port, "check_withdrawal_risk", {"entity_id": "CR84920"})
    assert got["recommendation"] == "PROPOSE_HOLD" and got["risk_score"] >= got["hold_threshold"]
    assert "intent_id" not in got
    assert got["units"]["risk_score"] == "ratio"


def test_account_without_a_pending_withdrawal_is_not_found(port: GovernedToolPort) -> None:
    outcome = port.call(AML, "check_withdrawal_risk", {"entity_id": "CR73491"})
    assert outcome.error is not None and outcome.error.code is ToolErrorCode.NOT_FOUND


def test_sar_draft_names_the_caller_and_is_marked_a_draft(port: GovernedToolPort) -> None:
    got = _ok(port, "draft_sar", {"entity_id": "CR84920"})
    assert got["investigator_id"] == "uid-test"
    assert got["status"] == "DRAFT" and got["requires_human_review"] is True
    assert got["cited_fact_ids"] and all(
        f.startswith("aml.dossier:CR84920:") for f in got["cited_fact_ids"]
    )
