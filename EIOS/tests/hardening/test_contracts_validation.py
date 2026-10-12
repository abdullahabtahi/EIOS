"""Tests for Phase 8: Strict JSON Schema Draft 2020-12 Contract Validation (T017)."""

from datetime import UTC, datetime
import pytest
import jsonschema

from eios.hardening.models import (
    ChaosExperimentRecord,
    ChaosExperimentStatus,
    DisasterRecoveryDrillReport,
    DRDrillStatus,
    SoakTestTelemetryReport,
    SecurityThreatDrillResult,
    STRIDECategory,
    RunbookExecutionProof,
    RunbookResolutionStatus,
)
from eios.hardening.schemas import (
    list_registered_schemas,
    validate_contract,
)


def test_registry_contains_all_five_schemas():
    """Verify schema validation registry contains all 5 hardening contracts."""
    schemas = list_registered_schemas()
    assert len(schemas) == 5
    expected_contracts = [
        "chaos-experiment-record.schema.json",
        "disaster-recovery-drill-report.schema.json",
        "soak-test-telemetry-report.schema.json",
        "security-threat-drill-result.schema.json",
        "runbook-execution-proof.schema.json",
    ]
    for contract in expected_contracts:
        assert contract in schemas


def test_chaos_experiment_record_contract():
    """Verify ChaosExperimentRecord serialization passes contract validation."""
    record = ChaosExperimentRecord(
        experiment_id="EXP-101",
        injection_type="PROCESS_CRASH",
        target_subsystem="hot_state",
        timestamp=datetime.now(UTC),
        parameters={"subsystem": "duckdb"},
        status=ChaosExperimentStatus.MITIGATED,
        detection_latency_ms=1.5,
        recovery_latency_ms=45.2,
        fallback_activated=False,
        assertions_passed=True,
        error_message=None,
    )
    dumped = record.model_dump(mode="json")
    assert validate_contract(dumped, "chaos-experiment-record") is True


def test_disaster_recovery_drill_report_contract():
    """Verify DisasterRecoveryDrillReport serialization passes contract validation."""
    report = DisasterRecoveryDrillReport(
        drill_id="DRILL-202",
        backup_snapshot_id="SNAP-999",
        drill_timestamp=datetime.now(UTC),
        status=DRDrillStatus.COMPLETED,
        rpo_achieved_minutes=1.2,
        rto_achieved_seconds=12.4,
        rpo_target_met=True,
        rto_target_met=True,
        restored_ledger_records=150,
        restored_graph_nodes=35,
        cryptographic_chain_valid=True,
        worm_root_hash="a" * 64,
    )
    dumped = report.model_dump(mode="json")
    assert validate_contract(dumped, "disaster-recovery-drill-report") is True


def test_soak_test_telemetry_report_contract():
    """Verify SoakTestTelemetryReport serialization passes contract validation."""
    report = SoakTestTelemetryReport(
        soak_id="SOAK-303",
        simulated_days=7.0,
        execution_duration_seconds=5.4,
        total_events_ingested=10500,
        total_queries_served=1050,
        total_actions_processed=525,
        initial_memory_mb=18.5,
        peak_memory_mb=22.1,
        final_memory_mb=19.0,
        memory_slope_mb_per_k_events=0.0012,
        is_leak_free=True,
        latency_p50_ms=2.1,
        latency_p95_ms=8.5,
        latency_p99_ms=18.2,
        slo_error_budgets_healthy=True,
    )
    dumped = report.model_dump(mode="json")
    assert validate_contract(dumped, "soak-test-telemetry-report") is True


def test_security_threat_drill_result_contract():
    """Verify SecurityThreatDrillResult serialization passes contract validation."""
    result = SecurityThreatDrillResult(
        drill_id="SEC-404",
        stride_category=STRIDECategory.SPOOFING,
        attack_vector="ForgedKMSIntentSignature",
        target_component="KMSActionSigner",
        bypass_attempted=True,
        attack_blocked=True,
        mitigation_verified="KMSValidator",
        audit_event_logged=True,
        timestamp=datetime.now(UTC),
    )
    dumped = result.model_dump(mode="json")
    assert validate_contract(dumped, "security-threat-drill-result") is True


def test_runbook_execution_proof_contract():
    """Verify RunbookExecutionProof serialization passes contract validation."""
    proof = RunbookExecutionProof(
        proof_id="PROOF-505",
        runbook_id="RUNBOOK-01",
        runbook_title="Contract Breach & DLQ Flood Triage",
        trigger_signal="DLQ queue depth > 500",
        diagnosis_summary="Malformed payloads isolated",
        mitigation_applied="Quarantined and replayed",
        time_to_mitigate_seconds=0.15,
        resolution_status=RunbookResolutionStatus.RESOLVED,
        post_incident_audit_verified=True,
        executed_at=datetime.now(UTC),
    )
    dumped = proof.model_dump(mode="json")
    assert validate_contract(dumped, "runbook-execution-proof") is True


def test_contract_validation_rejects_corrupted_payload():
    """Verify contract validation fails when required properties are missing."""
    corrupted_payload = {"invalid_key": "bad_data"}
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(corrupted_payload, "chaos-experiment-record")
