"""Unit and contract tests for LLM Gateway telemetry and Constitution Principle I Auditor Gate tracking."""

from __future__ import annotations

import pytest

from eios.observability.llm_telemetry import (
    AuditorVerdict,
    LLMTelemetryCollector,
    ModelPricingConfig,
    auditor_telemetry_to_contract_dict,
    llm_telemetry_to_contract_dict,
)
from eios.observability.schemas import validate_contract


def test_llm_invocation_recording_and_cost():
    """Verify LLM invocation metrics, token accounting, and deterministic USD cost calculations."""
    collector = LLMTelemetryCollector()
    collector.register_pricing(
        model_id="test-reasoning-model",
        pricing=ModelPricingConfig(
            prompt_cost_per_million=3.50,
            completion_cost_per_million=10.50,
            cached_cost_per_million=0.875,
        ),
    )

    record = collector.record_invocation(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        correlation_id="corr-llm-001",
        prompt_id="prompt-morning-briefing",
        prompt_version="1.2.0",
        model_id="test-reasoning-model",
        prompt_tokens=10_000,
        completion_tokens=2_000,
        cached_tokens=5_000,
        duration_ms=845.2,
    )

    assert record.prompt_tokens == 10_000
    assert record.completion_tokens == 2_000
    assert record.cached_tokens == 5_000
    # Expected cost: (10,000 * 3.50 + 2,000 * 10.50 + 5,000 * 0.875) / 1,000,000
    # = (35,000 + 21,000 + 4,375) / 1,000,000 = 60,375 / 1,000,000 = $0.060375
    assert pytest.approx(record.cost_usd, rel=1e-4) == 0.060375

    # Contract schema validation
    payload = llm_telemetry_to_contract_dict(record)
    assert validate_contract(payload, "llm-invocation-telemetry.schema.json") is True


def test_auditor_gate_passed_verdict():
    """Verify Auditor Gate telemetry records PASSED verdict when 100% of claims are cited."""
    collector = LLMTelemetryCollector()
    audit = collector.record_auditor_gate(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        correlation_id="corr-audit-001",
        text="The current financial fraud rate is 0.042% with $1,245,000 under active review.",
        total_claims_checked=2,
        verified_claims_count=2,
        unverified_claims_count=0,
        verdict=AuditorVerdict.PASSED,
        citation_references=["metric:financial_fraud_rate", "metric:active_review_volume"],
    )

    assert audit.verdict == AuditorVerdict.PASSED
    assert audit.unverified_claims_count == 0
    assert len(audit.text_hash) == 64  # SHA-256 hex string

    payload = auditor_telemetry_to_contract_dict(audit)
    assert validate_contract(payload, "auditor-gate-telemetry.schema.json") is True


def test_auditor_gate_rejected_verdict():
    """Verify Auditor Gate telemetry records REJECTED verdict on unverified hallucinated figures."""
    collector = LLMTelemetryCollector()
    audit = collector.record_auditor_gate(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        correlation_id="corr-audit-002",
        text="Estimated ungrounded loss is $88,000,000.",
        total_claims_checked=1,
        verified_claims_count=0,
        unverified_claims_count=1,
        verdict=AuditorVerdict.REJECTED,
        citation_references=[],
    )

    assert audit.verdict == AuditorVerdict.REJECTED
    assert audit.unverified_claims_count == 1

    payload = auditor_telemetry_to_contract_dict(audit)
    assert validate_contract(payload, "auditor-gate-telemetry.schema.json") is True


def test_telemetry_aggregate_spend_and_tokens():
    """Verify cumulative tokens and spend calculation across an enterprise correlation flow."""
    collector = LLMTelemetryCollector()
    collector.register_pricing(
        "model-a",
        ModelPricingConfig(prompt_cost_per_million=2.0, completion_cost_per_million=6.0),
    )

    collector.record_invocation(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        correlation_id="session-xyz",
        prompt_id="p1",
        prompt_version="1",
        model_id="model-a",
        prompt_tokens=1_000,
        completion_tokens=500,
        cached_tokens=0,
        duration_ms=200.0,
    )
    collector.record_invocation(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        correlation_id="session-xyz",
        prompt_id="p2",
        prompt_version="1",
        model_id="model-a",
        prompt_tokens=2_000,
        completion_tokens=1_000,
        cached_tokens=0,
        duration_ms=400.0,
    )

    summary = collector.get_correlation_summary("session-xyz")
    assert summary["total_calls"] == 2
    assert summary["total_prompt_tokens"] == 3_000
    assert summary["total_completion_tokens"] == 1_500
    # Cost 1: (1,000 * 2 + 500 * 6) / 1M = (2,000 + 3,000) / 1M = 0.005
    # Cost 2: (2,000 * 2 + 1,000 * 6) / 1M = (4,000 + 6,000) / 1M = 0.010
    # Total = 0.015
    assert pytest.approx(summary["total_cost_usd"], rel=1e-4) == 0.015
