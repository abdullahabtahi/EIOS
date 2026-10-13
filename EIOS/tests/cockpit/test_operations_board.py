"""Unit and contract tests for Data Platform & Operations Board (User Story 6)."""

import pytest

from eios.cockpit.operations import (
    DataPlatformOperationsService,
    DataProductHealthStatus,
)
from eios.cockpit.schemas import validate_contract
from eios.ontology.metrics.catalog import create_default_registry


def test_data_products_schema_contract_validation():
    """Verify that all DataProductSLAStatus instances validate against data-product-sla-status.schema.json."""
    svc = DataPlatformOperationsService()
    products = svc.get_data_products()

    assert len(products) >= 4
    for p in products:
        contract_dict = p.to_contract_dict()
        assert validate_contract(contract_dict, "data-product-sla-status") is True
        assert contract_dict["row_count"] >= 0
        assert 0.0 <= contract_dict["null_check_pass_rate"] <= 1.0
        assert contract_dict["status"] in ["HEALTHY", "DEGRADED", "BREACHED"]
        assert isinstance(contract_dict["is_degraded"], bool)


def test_freshness_sla_monitor_and_degraded_propagation():
    """Verify that simulating an SLA delay triggers DEGRADED or BREACHED status and alert cards."""
    svc = DataPlatformOperationsService()

    # Initial state should be healthy
    products = svc.get_data_products()
    client_tx = next(p for p in products if p.product_name == "client_transactions")
    assert client_tx.status == DataProductHealthStatus.HEALTHY
    assert client_tx.is_degraded is False

    # Simulate an ingestion lag of 400 seconds (SLA is 300s -> 400s is > 1x SLA -> DEGRADED)
    svc.simulate_sla_delay("client_transactions", delay_seconds=400)
    updated_products = svc.get_data_products()
    delayed_tx = next(p for p in updated_products if p.product_name == "client_transactions")

    assert delayed_tx.status == DataProductHealthStatus.DEGRADED
    assert delayed_tx.is_degraded is True

    # Check alert generation
    alerts = svc.get_contract_breach_alerts()
    assert any(
        a["product_name"] == "client_transactions" and a["severity"] == "WARNING" for a in alerts
    )

    # Simulate a critical lag of 700 seconds (> 2x SLA -> BREACHED)
    svc.simulate_sla_delay("client_transactions", delay_seconds=700)
    breached_products = svc.get_data_products()
    breached_tx = next(p for p in breached_products if p.product_name == "client_transactions")

    assert breached_tx.status == DataProductHealthStatus.BREACHED
    assert breached_tx.is_degraded is True

    critical_alerts = svc.get_contract_breach_alerts()
    assert any(
        a["product_name"] == "client_transactions" and a["severity"] == "CRITICAL"
        for a in critical_alerts
    )


def test_identity_cluster_conflict_resolution():
    """Verify inspection and resolution of cross-account entity identity conflicts."""
    svc = DataPlatformOperationsService()
    conflicts = svc.get_identity_cluster_conflicts()

    assert len(conflicts) >= 2
    conf = conflicts[0]
    assert conf["status"] == "UNRESOLVED"
    assert "DEVICE_FINGERPRINT_COLLISION" in conf["conflict_type"]
    assert conf["confidence_score"] >= 0.80

    # Resolve conflict via MERGE_PSEUDONYMIZED
    resolved = svc.resolve_identity_conflict(conf["conflict_id"], action="MERGE_PSEUDONYMIZED")
    assert resolved["status"] == "RESOLVED"
    assert resolved["resolution_action"] == "MERGE_PSEUDONYMIZED"
    assert "resolved_at" in resolved

    # Invalid action should raise ValueError
    with pytest.raises(ValueError):
        svc.resolve_identity_conflict("conf_alias_3310", action="INVALID_ACTION")


def test_semantic_metric_lineage_topology():
    """Verify end-to-end data lineage graph from source tables to consuming Cockpit widgets."""
    registry = create_default_registry()
    svc = DataPlatformOperationsService(metric_registry=registry)

    lineage = svc.get_metric_lineage("net_deposit_volume_usd")
    assert lineage["metric_id"] == "net_deposit_volume_usd"
    assert lineage["lineage_depth"] >= 4

    nodes = lineage["nodes"]
    node_types = {n["type"] for n in nodes}
    assert "INGESTION_SOURCE" in node_types
    assert "DATA_LAKE" in node_types
    assert "TRANSFORMATION" in node_types
    assert "DATA_PRODUCT" in node_types
    assert "GOVERNED_METRIC" in node_types
    assert "COCKPIT_WORKSTATION" in node_types

    edges = lineage["edges"]
    assert len(edges) >= 5


def test_board_summary():
    """Verify aggregated summary metrics for the Data Platform Operations Board."""
    svc = DataPlatformOperationsService()
    summary = svc.get_board_summary()

    assert summary["total_products"] >= 4
    assert summary["healthy_products"] >= 4
    assert summary["sla_compliance_rate_pct"] == 100.0
    assert summary["active_alerts_count"] == 0
    assert summary["unresolved_conflicts_count"] >= 2
