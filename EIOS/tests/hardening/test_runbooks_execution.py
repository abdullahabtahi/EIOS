"""Tests for User Story 5: Automated 10 Production Runbook Verification & OMCP Integration."""

from datetime import UTC, datetime
import pytest

from eios.hardening.models import RunbookExecutionProof, RunbookResolutionStatus
from eios.hardening.schemas import validate_contract
from eios.hardening.runbooks import RunbookVerificationEngine


def test_individual_runbook_execution():
    """Verify execution of Runbook 1 and Runbook 5 with certified proof generation."""
    engine = RunbookVerificationEngine()

    proof_1 = engine.execute_runbook("RUNBOOK-01")
    assert isinstance(proof_1, RunbookExecutionProof)
    assert proof_1.runbook_id == "RUNBOOK-01"
    assert proof_1.runbook_title == "Contract Breach & DLQ Flood Triage"
    assert proof_1.resolution_status == RunbookResolutionStatus.RESOLVED
    assert proof_1.post_incident_audit_verified is True
    assert proof_1.time_to_mitigate_seconds >= 0.0

    dumped_1 = proof_1.model_dump(mode="json")
    assert validate_contract(dumped_1, "runbook-execution-proof") is True

    proof_5 = engine.execute_runbook("RUNBOOK-05")
    assert proof_5.runbook_id == "RUNBOOK-05"
    assert proof_5.resolution_status == RunbookResolutionStatus.RESOLVED
    assert proof_5.post_incident_audit_verified is True
    assert validate_contract(proof_5.model_dump(mode="json"), "runbook-execution-proof") is True


def test_all_10_production_runbooks():
    """Verify automated execution of all 10 production runbooks from engagement plan §8."""
    engine = RunbookVerificationEngine()
    proofs = engine.execute_all_runbooks()

    assert len(proofs) == 10
    expected_ids = [f"RUNBOOK-{i:02d}" for i in range(1, 11)]

    for idx, proof in enumerate(proofs):
        assert proof.runbook_id == expected_ids[idx]
        assert proof.resolution_status == RunbookResolutionStatus.RESOLVED
        assert proof.post_incident_audit_verified is True
        assert proof.time_to_mitigate_seconds >= 0.0
        assert validate_contract(proof.model_dump(mode="json"), "runbook-execution-proof") is True


def test_unknown_runbook_rejection():
    """Verify invalid runbook ID raises KeyError."""
    engine = RunbookVerificationEngine()
    with pytest.raises(KeyError):
        engine.execute_runbook("RUNBOOK-99")


def test_omcp_get_hardening_drill_status():
    """Verify canonical OMCP tool get_hardening_drill_status dispatch (T016)."""
    from eios.ingestion.hot_state import HotStateEngine
    from eios.ontology.omcp.server import OMCPServer

    hot_state = HotStateEngine()
    server = OMCPServer(hot_state=hot_state)

    status = server.call_tool("get_hardening_drill_status", {"drill_type": "all"})
    assert status["status"] == "HEALTHY"
    assert status["disaster_recovery_ready"] is True
    assert status["stride_defenses_verified"] is True
    assert status["soak_slo_compliance"] is True
    assert status["registered_runbooks_count"] == 10
    assert "disaster_recovery" in status
    assert "runbook_catalog" in status
    assert len(status["runbook_catalog"]) == 10

