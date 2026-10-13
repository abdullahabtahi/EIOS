"""Tests for User Story 1: Chaos Engineering Injection & Resilient Degradation."""

from eios.hardening.models import ChaosExperimentRecord, ChaosExperimentStatus
from eios.hardening.schemas import validate_contract


def test_crash_recovery():
    from eios.hardening.chaos import ChaosEngine

    engine = ChaosEngine()
    record = engine.simulate_process_crash(target_subsystem="hot_state")

    assert isinstance(record, ChaosExperimentRecord)
    assert record.injection_type == "PROCESS_CRASH"
    assert record.status == ChaosExperimentStatus.MITIGATED
    assert record.recovery_latency_ms < 5000.0  # Warm-start under 5.0 seconds
    assert record.assertions_passed is True

    dumped = record.model_dump(mode="json")
    assert validate_contract(dumped, "chaos-experiment-record") is True


def test_dlq_poison_flood():
    from eios.hardening.chaos import ChaosEngine

    engine = ChaosEngine()
    record = engine.inject_dlq_flood(poison_count=100)

    assert record.injection_type == "DLQ_FLOOD"
    assert record.status == ChaosExperimentStatus.MITIGATED
    assert record.parameters["poison_count"] == 100
    assert record.parameters["quarantined_count"] == 100
    assert record.assertions_passed is True
    assert validate_contract(record.model_dump(mode="json"), "chaos-experiment-record") is True


def test_llm_outage_fallback():
    from eios.hardening.chaos import ChaosEngine

    engine = ChaosEngine()
    record = engine.simulate_llm_outage()

    assert record.injection_type == "LLM_OUTAGE"
    assert record.status == ChaosExperimentStatus.MITIGATED
    assert record.fallback_activated is True
    assert record.parameters["replay_badge_displayed"] is True
    assert record.assertions_passed is True
    assert validate_contract(record.model_dump(mode="json"), "chaos-experiment-record") is True


def test_duplicate_nonce_idempotency():
    from eios.hardening.chaos import ChaosEngine

    engine = ChaosEngine()
    record = engine.simulate_duplicate_delivery(intent_id="INTENT-REPLAY-99")

    assert record.injection_type == "DUPLICATE_NONCE"
    assert record.status == ChaosExperimentStatus.MITIGATED
    assert record.parameters["duplicate_rejected"] is True
    assert record.assertions_passed is True
    assert validate_contract(record.model_dump(mode="json"), "chaos-experiment-record") is True


def test_ledger_tamper_detection():
    from eios.hardening.chaos import ChaosEngine

    engine = ChaosEngine()
    record = engine.inject_ledger_tampering(target_seq=42)

    assert record.injection_type == "LEDGER_TAMPER"
    assert record.status == ChaosExperimentStatus.MITIGATED
    assert record.parameters["sev1_alert_raised"] is True
    assert record.parameters["approvals_halted"] is True
    assert record.assertions_passed is True
    assert validate_contract(record.model_dump(mode="json"), "chaos-experiment-record") is True
