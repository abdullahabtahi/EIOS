"""Exhaustive JSON Schema contract validation tests across all 6 Observability schemas."""

from __future__ import annotations

from datetime import datetime, timezone
import jsonschema
import pytest

from eios.observability.alerts import SREAlertEvent, SREAlertSeverity, alert_to_contract_dict
from eios.observability.golden_signals import (
    ServiceGoldenSignals,
    golden_signals_to_contract_dict,
)
from eios.observability.llm_telemetry import (
    AuditorGateTelemetry,
    AuditorVerdict,
    LLMInvocationTelemetry,
    auditor_telemetry_to_contract_dict,
    llm_telemetry_to_contract_dict,
)
from eios.observability.schemas import (
    list_registered_schemas,
    load_schema,
    validate_contract,
)
from eios.observability.slo_catalog import SLICategory
from eios.observability.slo_engine import (
    ErrorBudgetHealth,
    ErrorBudgetStatus,
    error_budget_to_contract_dict,
)
from eios.observability.tracing import (
    SpanStatus,
    TraceContextSpan,
    span_to_contract_dict,
)


def test_registered_schemas_count():
    """Verify all 6 contract schemas are registered in contracts directory."""
    schemas = list_registered_schemas()
    assert len(schemas) == 6
    expected = {
        "auditor-gate-telemetry.schema.json",
        "error-budget-status.schema.json",
        "llm-invocation-telemetry.schema.json",
        "service-golden-signals.schema.json",
        "sre-alert-event.schema.json",
        "trace-context-span.schema.json",
    }
    assert set(schemas) == expected


def test_contract_trace_context_span_valid_and_invalid():
    """Verify trace-context-span schema validation and error detection."""
    now = datetime.now(timezone.utc)
    valid_span = TraceContextSpan(
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        parent_span_id="5a1b2c3d4e5f6071",
        correlation_id="corr-val-1",
        service_name="test_service",
        operation_name="op",
        start_time=now,
        end_time=now,
        duration_ms=12.5,
        status=SpanStatus.OK,
    )
    payload = span_to_contract_dict(valid_span)
    assert validate_contract(payload, "trace-context-span.schema.json") is True

    # Invalid trace_id pattern/length
    bad_payload = dict(payload)
    bad_payload["trace_id"] = "too-short"
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_payload, "trace-context-span.schema.json")


def test_contract_error_budget_status_valid_and_invalid():
    """Verify error-budget-status schema validation and error detection."""
    valid_status = ErrorBudgetStatus(
        sli_name=SLICategory.INGESTION_FRESHNESS,
        window_days=28,
        total_events=1000,
        compliant_events=995,
        failed_events=5,
        compliance_percentage=99.5,
        target_percentage=99.0,
        budget_remaining_pct=50.0,
        burn_rate_1h=0.5,
        burn_rate_6h=0.4,
        burn_rate_24h=0.5,
        status=ErrorBudgetHealth.HEALTHY,
        is_frozen=False,
    )
    payload = error_budget_to_contract_dict(valid_status)
    assert validate_contract(payload, "error-budget-status.schema.json") is True

    # Invalid status enum
    bad_payload = dict(payload)
    bad_payload["status"] = "INVALID_STATUS"
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_payload, "error-budget-status.schema.json")


def test_contract_sre_alert_event_valid_and_invalid():
    """Verify sre-alert-event schema validation and error detection."""
    now = datetime.now(timezone.utc)
    valid_alert = SREAlertEvent(
        alert_id="alert-uuid-1",
        policy_name="Multi-Burn 14.4x",
        severity=SREAlertSeverity.PAGE_CRITICAL_SEV1,
        sli_name=SLICategory.METRIC_QUERY_LATENCY,
        service_name="omcp_server",
        burn_rate=15.2,
        message="Critical burn rate alert",
        triggered_at=now,
        is_active=True,
    )
    payload = alert_to_contract_dict(valid_alert)
    assert validate_contract(payload, "sre-alert-event.schema.json") is True

    # Negative burn_rate
    bad_payload = dict(payload)
    bad_payload["burn_rate"] = -5.0
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_payload, "sre-alert-event.schema.json")


def test_contract_llm_invocation_telemetry_valid_and_invalid():
    """Verify llm-invocation-telemetry schema validation and error detection."""
    now = datetime.now(timezone.utc)
    valid_llm = LLMInvocationTelemetry(
        call_id="call-123",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        correlation_id="corr-llm",
        prompt_id="prompt-1",
        prompt_version="1.0.0",
        model_id="test-reasoning-model",
        prompt_tokens=500,
        completion_tokens=200,
        cached_tokens=0,
        duration_ms=450.0,
        cost_usd=0.0035,
        timestamp=now,
    )
    payload = llm_telemetry_to_contract_dict(valid_llm)
    assert validate_contract(payload, "llm-invocation-telemetry.schema.json") is True

    # Negative tokens
    bad_payload = dict(payload)
    bad_payload["prompt_tokens"] = -1
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_payload, "llm-invocation-telemetry.schema.json")


def test_contract_auditor_gate_telemetry_valid_and_invalid():
    """Verify auditor-gate-telemetry schema validation and error detection."""
    now = datetime.now(timezone.utc)
    valid_audit = AuditorGateTelemetry(
        audit_id="aud-1",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        correlation_id="corr-aud",
        text_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        total_claims_checked=3,
        verified_claims_count=3,
        unverified_claims_count=0,
        verdict=AuditorVerdict.PASSED,
        citation_references=["metric:1", "metric:2"],
        evaluated_at=now,
    )
    payload = auditor_telemetry_to_contract_dict(valid_audit)
    assert validate_contract(payload, "auditor-gate-telemetry.schema.json") is True

    # Invalid verdict
    bad_payload = dict(payload)
    bad_payload["verdict"] = "MAYBE"
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_payload, "auditor-gate-telemetry.schema.json")


def test_contract_service_golden_signals_valid_and_invalid():
    """Verify service-golden-signals schema validation and error detection."""
    now = datetime.now(timezone.utc)
    valid_signals = ServiceGoldenSignals(
        service_name="omcp_server",
        timestamp=now,
        requests_per_second=150.0,
        latency_p50_ms=45.0,
        latency_p90_ms=120.0,
        latency_p95_ms=180.0,
        latency_p99_ms=350.0,
        error_rate_pct=0.2,
        saturation_pct=42.0,
        is_saturated=False,
    )
    payload = golden_signals_to_contract_dict(valid_signals)
    assert validate_contract(payload, "service-golden-signals.schema.json") is True

    # Out-of-range saturation percentage (> 100)
    bad_payload = dict(payload)
    bad_payload["saturation_pct"] = 105.0
    with pytest.raises(jsonschema.ValidationError):
        validate_contract(bad_payload, "service-golden-signals.schema.json")
