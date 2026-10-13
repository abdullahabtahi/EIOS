"""Tests for User Story 2: Automated Disaster Recovery (DR) & Failover Drill."""

from eios.hardening.dr import DisasterRecoveryCoordinator
from eios.hardening.models import DisasterRecoveryDrillReport, DRDrillStatus
from eios.hardening.schemas import validate_contract
from eios.ontology.actions.models import LedgerEventType


def test_cold_storage_snapshot_and_restore():
    """Verify snapshot export, clean site teardown, and clean-site rehydration."""
    coordinator = DisasterRecoveryCoordinator()

    # Populate some ledger events
    for i in range(10):
        coordinator.sequencer.record_event(
            event_type=LedgerEventType.PROPOSAL_CREATED,
            entity_id=f"CLIENT-{i:03d}",
            payload={"action": "FreezeAccount", "index": i},
        )
    # Add dummy graph nodes
    coordinator.property_graph.graph.add_node("PARTNER-001", node_type="partner")
    coordinator.property_graph.graph.add_node("DEV-001", node_type="device")
    coordinator.property_graph.graph.add_edge("PARTNER-001", "DEV-001", edge_type="device_link")

    # Snapshot
    snapshot_id = coordinator.create_snapshot()
    assert snapshot_id.startswith("SNAP-")
    assert snapshot_id in coordinator.snapshots

    # Teardown
    coordinator.teardown_site()
    assert coordinator.sequencer.current_seq == 0
    assert coordinator.property_graph.node_count == 0

    # Restore
    summary = coordinator.restore_from_snapshot(snapshot_id)
    assert summary["restored_ledger_records"] == 10
    assert summary["restored_graph_nodes"] >= 2
    assert coordinator.sequencer.current_seq == 10
    assert coordinator.property_graph.has_node("PARTNER-001")


def test_forensic_chain_continuity():
    """Verify SHA-256 Merkle root and hash chain integrity during restore."""
    coordinator = DisasterRecoveryCoordinator()
    for i in range(5):
        coordinator.sequencer.record_event(
            event_type=LedgerEventType.APPROVAL_RECORDED,
            entity_id=f"CLIENT-{i}",
            payload={"approved": True, "idx": i},
        )

    snapshot_id = coordinator.create_snapshot()
    coordinator.teardown_site()
    coordinator.restore_from_snapshot(snapshot_id)

    valid, root_hash = coordinator.verify_forensic_continuity(snapshot_id)
    assert valid is True
    assert len(root_hash) == 64


def test_rpo_and_rto_drill_compliance():
    """Verify failover drill achieves RPO <= 15 minutes and RTO <= 2 hours (<= 30s in test)."""
    coordinator = DisasterRecoveryCoordinator()
    for i in range(20):
        coordinator.sequencer.record_event(
            event_type=LedgerEventType.ACTION_EXECUTED,
            entity_id=f"TXN-{i}",
            payload={"amount": 100.0 * i},
        )

    report = coordinator.run_failover_drill()

    assert isinstance(report, DisasterRecoveryDrillReport)
    assert report.status == DRDrillStatus.COMPLETED
    assert report.rpo_achieved_minutes <= 15.0
    assert report.rto_achieved_seconds <= 7200.0
    assert report.rpo_target_met is True
    assert report.rto_target_met is True
    assert report.restored_ledger_records == 20
    assert report.cryptographic_chain_valid is True
    assert len(report.worm_root_hash) == 64

    # Contract validation
    dumped = report.model_dump(mode="json")
    assert validate_contract(dumped, "disaster-recovery-drill-report") is True
