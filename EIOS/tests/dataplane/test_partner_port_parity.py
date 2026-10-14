"""On the engine plane the partner tools read the radar the screen renders, for any partner (spec 032 SC-003)."""

from typing import Any

import pytest

from eios.cockpit.aml import AMLWorkstationService
from eios.dataplane.partner_service import EnginePartnerService
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import DataOrigin, ToolErrorCode
from eios.ontology.omcp.port.principal import Principal, principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort

PM: Principal = principal_for("uid-test", "partner_manager")


@pytest.fixture(scope="module")
def port(partner_service: EnginePartnerService) -> GovernedToolPort:
    return build_port(ReadModels.over(AMLWorkstationService(), partner=partner_service))


def _ok(port: GovernedToolPort, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    outcome = port.call(PM, tool, args)
    assert outcome.error is None, outcome.error
    return outcome.payload()


def _others(svc: EnginePartnerService) -> list[str]:
    radar = svc.get_churn_radar_scatter().partners
    return [p.partner_id for p in radar if p.churn_hazard_probability >= 0.5][3:8]


def test_signals_equal_the_radar_for_partners_beyond_the_story(
    port: GovernedToolPort, partner_service: EnginePartnerService
) -> None:
    radar = {p.partner_id: p for p in partner_service.get_churn_radar_scatter().partners}
    for pid in _others(partner_service):
        got = _ok(port, "get_partner_signals", {"entity_id": pid})
        assert got["data_origin"] == DataOrigin.ENGINE.value
        assert got["churn_hazard_probability"] == radar[pid].churn_hazard_probability
        assert got["realized_volume_30d_usd"] == radar[pid].realized_volume_30d_usd
        assert len(got["retention_deals"]) == len(partner_service.get_retention_playbooks(pid))


def test_the_worklist_ranks_by_expected_loss_from_the_engine(port: GovernedToolPort) -> None:
    got = _ok(port, "list_partner_worklist", {"limit": 10})
    losses = [p["expected_loss_usd"] for p in got["partners"]]
    assert losses == sorted(losses, reverse=True) and got["data_origin"] == DataOrigin.ENGINE.value


def test_integrity_and_comms_are_served_for_any_partner(
    port: GovernedToolPort, partner_service: EnginePartnerService
) -> None:
    pid = _others(partner_service)[0]
    integrity = _ok(port, "get_partner_integrity", {"entity_id": pid})
    assert integrity["statement"].startswith("Observed patterns only")
    comms = port.call(PM, "read_partner_comms", {"entity_id": "PTR-882"})
    assert comms.error is None
    body = comms.payload()
    assert body["untrusted"] is True and all(m["untrusted"] for m in body["messages"])


def test_a_deal_can_be_proposed_for_any_partner_with_a_playbook(
    port: GovernedToolPort, partner_service: EnginePartnerService
) -> None:
    pid = next(p for p in _others(partner_service) if partner_service.get_retention_playbooks(p))
    deal = partner_service.get_retention_playbooks(pid)[0]
    got = _ok(port, "propose_partner_action", {"entity_id": pid, "playbook_id": deal.playbook_id})
    assert got["estimated_cost_usd"] == deal.estimated_cost_usd and got["data_origin"] == "engine"
    missing = port.call(PM, "propose_partner_action", {"entity_id": pid, "playbook_id": "pb_nope"})
    assert missing.error is not None and missing.error.code is ToolErrorCode.NOT_FOUND
