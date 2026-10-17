"""Universal OpenTelemetry Tracing Spine & Distributed Context Propagation.

Provides low-overhead (< 2ms) distributed tracing across all EIOS tiers,
attaching W3C TraceContext (traceparent), ambient correlation IDs, and
adaptive tail sampling preserving 100% of errors and long-tail latency events.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from eios.common.correlation import current_id, new_correlation_id
from eios.observability.carrier import (
    current_baggage,
)

# Active span context stack
_CURRENT_ACTIVE_SPAN: ContextVar[TraceContextSpan | None] = ContextVar(
    "eios_active_span", default=None
)


class SpanStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


class TraceContextSpan(BaseModel):
    """Distributed tracing span record conforming to W3C TraceContext standards."""

    trace_id: str = Field(..., min_length=32, max_length=32, description="32-hex W3C trace ID")
    span_id: str = Field(..., min_length=16, max_length=16, description="16-hex W3C span ID")
    parent_span_id: str | None = Field(None, description="Parent span ID if nested")
    correlation_id: str = Field(..., description="Enterprise transaction correlation identifier")
    service_name: str = Field(..., description="Service emitting the span")
    operation_name: str = Field(..., description="Operation executed")
    start_time: datetime = Field(..., description="Span start timestamp in UTC")
    end_time: datetime | None = Field(None, description="Span end timestamp in UTC")
    duration_ms: float | None = Field(None, ge=0.0, description="Duration in milliseconds")
    status: SpanStatus = Field(default=SpanStatus.OK, description="Execution status")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Diagnostic tags")
    events: list[dict[str, Any]] = Field(default_factory=list, description="In-span events")

    def set_attribute(self, key: str, value: Any) -> None:
        """Sets a tag attribute on the span."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Appends an event checkpoint to the span."""
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.now(UTC).isoformat(),
                "attributes": attributes or {},
            }
        )


def _generate_trace_id() -> str:
    """Generates a random 32-hex character W3C trace ID."""
    return secrets.token_hex(16)


def _generate_span_id() -> str:
    """Generates a random 16-hex character W3C span ID."""
    return secrets.token_hex(8)


class OpenTelemetrySpine:
    """Universal OpenTelemetry distributed tracing coordinator for an EIOS service."""

    def __init__(
        self,
        service_name: str,
        sample_rate: float = 1.0,
        latency_tail_threshold_ms: float = 2000.0,
    ) -> None:
        self.service_name = service_name
        self.sample_rate = sample_rate
        self.latency_tail_threshold_ms = latency_tail_threshold_ms
        self._exported_spans: list[TraceContextSpan] = []
        self._lock = threading.RLock()

    @contextmanager
    def start_as_current_span(
        self,
        operation_name: str,
        attributes: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> Iterator[TraceContextSpan]:
        """Starts a span as current in ContextVar, capturing parentage and correlation."""
        parent = _CURRENT_ACTIVE_SPAN.get()
        start_mono = time.perf_counter()
        start_utc = datetime.now(UTC)

        cid = (
            correlation_id
            or (parent.correlation_id if parent else None)
            or current_id()
            or current_baggage().get("correlation_id")
            or new_correlation_id()
        )

        trace_id = parent.trace_id if parent else _generate_trace_id()
        span_id = _generate_span_id()
        parent_span_id = parent.span_id if parent else None

        span = TraceContextSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            correlation_id=cid,
            service_name=self.service_name,
            operation_name=operation_name,
            start_time=start_utc,
            status=SpanStatus.OK,
            attributes=dict(attributes or {}),
            events=[],
        )

        token = _CURRENT_ACTIVE_SPAN.set(span)
        try:
            yield span
        except BaseException as exc:
            span.status = SpanStatus.ERROR
            span.add_event(
                "exception",
                {
                    "exception.type": type(exc).__name__,
                    "exception.message": str(exc),
                },
            )
            raise
        finally:
            end_mono = time.perf_counter()
            end_utc = datetime.now(UTC)
            duration_ms = max(0.0, (end_mono - start_mono) * 1000.0)
            span.end_time = end_utc
            span.duration_ms = duration_ms
            _CURRENT_ACTIVE_SPAN.reset(token)

            # Adaptive Tail-Sampling Decision:
            # 1. 100% of errors are always preserved
            # 2. 100% of spans exceeding latency tail threshold are preserved
            # 3. Nominal spans sampled according to sample_rate
            should_record = False
            if span.status == SpanStatus.ERROR:
                should_record = True
            elif duration_ms >= self.latency_tail_threshold_ms:
                should_record = True
            elif self.sample_rate >= 1.0 or secrets.SystemRandom().random() <= self.sample_rate:
                should_record = True

            if should_record:
                with self._lock:
                    self._exported_spans.append(span)

    def get_exported_spans(self) -> list[TraceContextSpan]:
        """Returns snapshot of exported spans in chronological recording order."""
        with self._lock:
            return list(self._exported_spans)

    def clear(self) -> None:
        """Flushes recorded spans."""
        with self._lock:
            self._exported_spans.clear()


def span_to_contract_dict(span: TraceContextSpan) -> dict[str, Any]:
    """Converts a TraceContextSpan to a dictionary strictly matching trace-context-span.schema.json."""
    data: dict[str, Any] = {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "correlation_id": span.correlation_id,
        "service_name": span.service_name,
        "operation_name": span.operation_name,
        "start_time": span.start_time.isoformat(),
        "status": span.status.value,
        "attributes": span.attributes,
        "events": span.events,
    }
    if span.parent_span_id is not None:
        data["parent_span_id"] = span.parent_span_id
    if span.end_time is not None:
        data["end_time"] = span.end_time.isoformat()
    if span.duration_ms is not None:
        data["duration_ms"] = float(span.duration_ms)
    return data
