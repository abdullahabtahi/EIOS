"""Unit and contract tests for the OpenTelemetry distributed tracing spine and context carrier."""

from __future__ import annotations

from datetime import datetime, timezone
import time
import pytest

from eios.observability.carrier import (
    W3C_TRACEPARENT_HEADER,
    W3C_BAGGAGE_HEADER,
    ambient_context_scope,
    extract_context,
    format_baggage,
    format_traceparent,
    inject_context,
    parse_baggage,
    parse_traceparent,
)
from eios.observability.schemas import validate_contract
from eios.observability.tracing import (
    OpenTelemetrySpine,
    SpanStatus,
    TraceContextSpan,
    span_to_contract_dict,
)


def test_w3c_traceparent_format_and_parse():
    """Verify standard 00-version W3C traceparent formatting and parsing."""
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    span_id = "00f067aa0ba902b7"
    tp = format_traceparent(trace_id, span_id, sampled=True)
    assert tp == f"00-{trace_id}-{span_id}-01"

    parsed = parse_traceparent(tp)
    assert parsed is not None
    version, t_id, s_id, flags = parsed
    assert version == "00"
    assert t_id == trace_id
    assert s_id == span_id
    assert flags == "01"

    # Malformed traceparent should return None
    assert parse_traceparent("invalid-traceparent") is None
    # All zero trace_id is illegal in W3C v00
    assert parse_traceparent("00-00000000000000000000000000000000-00f067aa0ba902b7-01") is None


def test_w3c_baggage_format_and_parse():
    """Verify standard W3C baggage header key-value formatting and parsing."""
    items = {"correlation_id": "corr-xyz", "tenant": "enterprise-a", "user": "alice"}
    bag_str = format_baggage(items)
    parsed = parse_baggage(bag_str)
    assert parsed["correlation_id"] == "corr-xyz"
    assert parsed["tenant"] == "enterprise-a"
    assert parsed["user"] == "alice"


def test_ambient_context_propagation():
    """Verify ambient correlation ID and baggage injection and extraction across headers."""
    with ambient_context_scope(correlation_id="corr-enterprise-999", baggage={"app": "cockpit"}):
        outbound = inject_context({"User-Agent": "EIOS-Cockpit"})
        assert outbound["X-Correlation-ID"] == "corr-enterprise-999"
        assert "correlation_id=corr-enterprise-999" in outbound[W3C_BAGGAGE_HEADER]
        assert "app=cockpit" in outbound[W3C_BAGGAGE_HEADER]

        # Extract on receiving service side
        extracted = extract_context(outbound)
        assert extracted.correlation_id == "corr-enterprise-999"
        assert extracted.baggage["app"] == "cockpit"


def test_tracing_spine_root_and_child_spans():
    """Verify hierarchical span creation, parent-child link, and timing in OpenTelemetrySpine."""
    spine = OpenTelemetrySpine(service_name="test_service")

    with ambient_context_scope(correlation_id="corr-flow-001"):
        with spine.start_as_current_span("parent_op") as parent:
            assert parent.correlation_id == "corr-flow-001"
            assert parent.service_name == "test_service"
            assert parent.operation_name == "parent_op"

            # Simulate work
            time.sleep(0.01)

            with spine.start_as_current_span("child_op") as child:
                assert child.correlation_id == "corr-flow-001"
                assert child.parent_span_id == parent.span_id
                assert child.trace_id == parent.trace_id
                assert child.operation_name == "child_op"
                time.sleep(0.005)

    spans = spine.get_exported_spans()
    assert len(spans) == 2

    # Spans are recorded upon exit: child finishes before parent
    child_span = spans[0]
    parent_span = spans[1]
    assert child_span.operation_name == "child_op"
    assert parent_span.operation_name == "parent_op"
    assert child_span.parent_span_id == parent_span.span_id
    assert child_span.duration_ms is not None and child_span.duration_ms >= 4.0
    assert parent_span.duration_ms is not None and parent_span.duration_ms >= 14.0


def test_tracing_spine_error_capture_and_tail_sampling():
    """Verify error status and exception event recording, plus adaptive tail sampling retention."""
    spine = OpenTelemetrySpine(service_name="error_service", sample_rate=0.0)  # nominal spans dropped

    # 1. Error span should be retained despite 0.0 nominal sample rate
    with pytest.raises(RuntimeError):
        with spine.start_as_current_span("failing_op") as span:
            span.set_attribute("stage", "validation")
            raise RuntimeError("Database connection timeout")

    spans = spine.get_exported_spans()
    assert len(spans) == 1
    err_span = spans[0]
    assert err_span.status == SpanStatus.ERROR
    assert err_span.attributes["stage"] == "validation"
    assert any(e.get("name") == "exception" for e in err_span.events)


def test_tracing_spine_contract_schema_compliance():
    """Verify span serialization adheres to trace-context-span.schema.json."""
    spine = OpenTelemetrySpine(service_name="omcp_server")
    with ambient_context_scope(correlation_id="corr-contract-test"):
        with spine.start_as_current_span("resolve_provenance") as span:
            span.set_attribute("metric_id", "financial_fraud_rate")
            span.add_event("cache_hit", {"latency_us": 45})

    spans = spine.get_exported_spans()
    assert len(spans) == 1
    span_obj = spans[0]

    # Convert to contract payload and validate with jsonschema Draft 2020-12
    payload = span_to_contract_dict(span_obj)
    assert validate_contract(payload, "trace-context-span.schema.json") is True


def test_tracing_spine_overhead_sub_2ms():
    """Verify span creation and teardown overhead is strictly < 2.0 ms (target from spec)."""
    spine = OpenTelemetrySpine(service_name="bench_service")
    iterations = 200
    t0 = time.perf_counter()
    for _ in range(iterations):
        with spine.start_as_current_span("bench_op"):
            pass
    avg_ms = ((time.perf_counter() - t0) * 1000.0) / iterations
    assert avg_ms < 2.0

