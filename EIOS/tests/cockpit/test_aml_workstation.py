"""Tests for AML Investigator Workstation: Triage, Dossier, Kinetic Graph, and SAR Draft."""

from eios.cockpit.aml import AMLWorkstationService
from eios.cockpit.schemas import validate_contract


def test_triage_queue():
    svc = AMLWorkstationService()
    queue = svc.get_triage_queue(min_score=60)
    assert len(queue) >= 2
    assert queue[0]["entity_id"] == "CR84920"
    assert queue[0]["risk_score"] >= queue[1]["risk_score"]


def test_aml_entity_dossier_contract():
    svc = AMLWorkstationService()
    dossier = svc.get_entity_dossier("CR84920")

    assert dossier.entity_id == "CR84920"
    assert dossier.composite_risk_score == 89
    assert dossier.discrepancy.discrepancy_multiplier == 16.0
    assert dossier.syndicate_ring_size == 23
    assert dossier.dowhy_refuter_confirmed is True

    contract_dict = dossier.to_contract_dict()
    assert validate_contract(contract_dict, "entity-investigation-dossier") is True


def test_kinetic_network_graph_hub_suppression_contract():
    svc = AMLWorkstationService()
    graph = svc.get_kinetic_network_graph("CR84920", hub_threshold=100)

    assert graph.seed_entity_id == "CR84920"
    assert len(graph.nodes) >= 3
    assert len(graph.edges) >= 2

    # Verify supernode has hub suppression activated
    hub = next(n for n in graph.nodes if n.node_id == "PA-HUB-007")
    assert hub.degree > 100
    assert hub.is_hub_suppressed is True
    assert hub.collapsed_node_count == 46

    contract_dict = graph.to_contract_dict()
    assert validate_contract(contract_dict, "kinetic-network-graph") is True


def test_sar_draft_document_contract():
    svc = AMLWorkstationService()
    sar = svc.compose_sar_draft("case_aml_84920", "CR84920", "INV-042")

    assert sar.subject_entity_id == "CR84920"
    assert "31 CFR 1010" in sar.statutory_citations
    assert "realized_deposit_volume_30d_usd" in sar.cited_metric_ids
    assert "16.0x" in sar.narrative_summary

    contract_dict = sar.to_contract_dict()
    assert validate_contract(contract_dict, "sar-draft-document") is True
