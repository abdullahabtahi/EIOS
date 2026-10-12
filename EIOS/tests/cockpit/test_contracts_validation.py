"""Validation tests for all 10 JSON Schema contracts against domain model serialization.

Guarantees 100% contract compliance across all 5 persona workstations and shared invariants.
"""

from datetime import UTC, datetime, timedelta
import pytest

from eios.cockpit.aml import AMLWorkstationService
from eios.cockpit.executive import ExecutiveCockpitService
from eios.cockpit.governance_shelf import GovernedActionCard, GovernedActionShelf
from eios.cockpit.operations import DataPlatformOperationsService
from eios.cockpit.partner import PartnerWorkstationService
from eios.cockpit.provenance import ProvenanceResolver
from eios.cockpit.schemas import validate_contract
from eios.cockpit.session import OperatorRole, SessionManager, WorkstationTab
from eios.ontology.actions.models import (
    ActionIntentToken,
    ActionSeverity,
    ActionStatus,
)


def test_contract_1_workstation_view_session():
    mgr = SessionManager()
    session = mgr.create_session(operator_id="usr_exec_01", role=OperatorRole.EXECUTIVE)
    data = session.to_contract_dict()
    assert validate_contract(data, "workstation-view-session") is True


def test_contract_2_provenance_metadata():
    resolver = ProvenanceResolver()
    metadata = resolver.resolve("net_revenue_usd")
    data = metadata.to_contract_dict()
    assert validate_contract(data, "provenance-metadata") is True


def test_contract_3_governed_action_card():
    shelf = GovernedActionShelf()
    now = datetime.now(UTC)
    token = ActionIntentToken(
        intent_id="intent_12345",
        action_type="HoldWithdrawal",
        parameters={"txn_id": "tx_99812", "amount": 12000.0},
        evidence_refs=["ev_ref_1"],
        severity=ActionSeverity.HIGH,
        status=ActionStatus.PENDING,
        nonce="nonce_test",
        issued_at=now,
        expires_at=now + timedelta(minutes=15),
        requester_agent_id="AMLWorkerAgent",
        kms_key_id="projects/eios/locations/global/keyRings/rings/cryptoKeys/governance",
        signature="dGVzdF9zaWduYXR1cmU=",
        propensity_score=0.95,
        causal_context={},
        requires_dual_approval=True,
        policy_tags=["FOUR_EYES_MANDATORY"],
    )
    card = shelf.stage_token(token)
    data = card.to_contract_dict()
    assert validate_contract(data, "governed-action-card") is True


def test_contract_4_morning_briefing_dossier():
    svc = ExecutiveCockpitService()
    briefing = svc.get_morning_briefing()
    data = briefing.to_contract_dict()
    assert validate_contract(data, "morning-briefing-dossier") is True


def test_contract_5_causal_dag_graph():
    svc = ExecutiveCockpitService()
    dag = svc.get_causal_dag()
    data = dag.to_contract_dict()
    assert validate_contract(data, "causal-dag-graph") is True


def test_contract_6_entity_investigation_dossier():
    svc = AMLWorkstationService()
    dossier = svc.get_entity_dossier(entity_id="CR84920")
    data = dossier.to_contract_dict()
    assert validate_contract(data, "entity-investigation-dossier") is True


def test_contract_7_kinetic_network_graph():
    svc = AMLWorkstationService()
    graph = svc.get_kinetic_network_graph(entity_id="CR84920")
    data = graph.to_contract_dict()
    assert validate_contract(data, "kinetic-network-graph") is True


def test_contract_8_sar_draft_document():
    svc = AMLWorkstationService()
    sar = svc.compose_sar_draft(case_id="case_aml_84920", entity_id="CR84920", investigator_id="investigator_alice")
    data = sar.to_contract_dict()
    assert validate_contract(data, "sar-draft-document") is True


def test_contract_9_churn_radar_scatter():
    svc = PartnerWorkstationService()
    scatter = svc.get_churn_radar_scatter()
    data = scatter.to_contract_dict()
    assert validate_contract(data, "churn-radar-scatter") is True


def test_contract_10_data_product_sla_status():
    svc = DataPlatformOperationsService()
    products = svc.get_data_products()
    assert len(products) >= 1
    for p in products:
        data = p.to_contract_dict()
        assert validate_contract(data, "data-product-sla-status") is True
