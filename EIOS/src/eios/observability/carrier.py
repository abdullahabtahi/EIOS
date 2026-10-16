"""W3C TraceContext Propagator and Ambient Correlation Baggage Carrier.

Provides W3C TraceContext (traceparent, tracestate) and W3C Baggage header injection/extraction,
harmonized with ambient enterprise correlation IDs (X-Correlation-ID) and ContextVar scopes.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from opentelemetry.context import Context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from eios.common.correlation import (
    CORRELATION_HEADER,
    correlation_scope,
    current_id,
    new_correlation_id,
    resolve_inbound_id,
)

W3C_TRACEPARENT_HEADER = "traceparent"
W3C_TRACESTATE_HEADER = "tracestate"
W3C_BAGGAGE_HEADER = "baggage"

_TRACEPARENT_PATTERN = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")

_PROPAGATOR = TraceContextTextMapPropagator()

# Task-local baggage store
_CURRENT_BAGGAGE: ContextVar[dict[str, str] | None] = ContextVar("eios_baggage", default=None)


@dataclass(frozen=True)
class ExtractedContext:
    """Carries distributed context extracted from inbound headers."""

    trace_id: str | None
    span_id: str | None
    trace_flags: str | None
    correlation_id: str
    baggage: dict[str, str] = field(default_factory=dict)
    otel_context: Context = field(default_factory=Context)


def parse_traceparent(traceparent: str) -> tuple[str, str, str, str] | None:
    """Parses W3C traceparent header into (version, trace_id, parent_id, flags).

    Returns None if malformed or non-compliant with W3C specification.
    """
    if not isinstance(traceparent, str):
        return None
    match = _TRACEPARENT_PATTERN.match(traceparent.strip().lower())
    if not match:
        return None
    version, trace_id, parent_id, flags = match.groups()
    # W3C spec: version 00 must not have all-zero trace_id or span_id
    if version == "00" and (trace_id == "0" * 32 or parent_id == "0" * 16):
        return None
    return version, trace_id, parent_id, flags


def format_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    """Formats compliant W3C traceparent header string."""
    flags = "01" if sampled else "00"
    return f"00-{trace_id:0>32}-{span_id:0>16}-{flags}"


def parse_baggage(baggage_str: str) -> dict[str, str]:
    """Parses W3C baggage header key=value pairs."""
    items: dict[str, str] = {}
    if not baggage_str:
        return items
    for entry in baggage_str.split(","):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("=", 1)
        if len(parts) == 2:
            key = parts[0].strip()
            val = parts[1].strip()
            if key:
                items[key] = val
    return items


def format_baggage(items: Mapping[str, str]) -> str:
    """Formats dictionary into W3C baggage header string."""
    return ",".join(f"{k}={v}" for k, v in items.items() if k and v)


def current_baggage() -> dict[str, str]:
    """Returns a copy of current task-local baggage."""
    return dict(_CURRENT_BAGGAGE.get() or {})


@contextmanager
def ambient_context_scope(
    correlation_id: str | None = None,
    baggage: Mapping[str, str] | None = None,
) -> Iterator[None]:
    """Binds correlation ID and ambient baggage to current task."""
    cid = (
        resolve_inbound_id(correlation_id)
        if correlation_id
        else (current_id() or new_correlation_id())
    )
    new_bag = dict(_CURRENT_BAGGAGE.get() or {})
    if baggage:
        new_bag.update(baggage)
    new_bag["correlation_id"] = cid

    bag_token = _CURRENT_BAGGAGE.set(new_bag)
    with correlation_scope(cid):
        try:
            yield
        finally:
            _CURRENT_BAGGAGE.reset(bag_token)


def inject_context(
    headers: Mapping[str, str] | None = None,
    correlation_id: str | None = None,
    baggage: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Injects W3C traceparent, baggage, and X-Correlation-ID into outbound headers."""
    carrier: dict[str, str] = dict(headers or {})

    # 1. Inject W3C TraceContext from active OpenTelemetry context
    _PROPAGATOR.inject(carrier)

    # 2. Resolve correlation ID
    curr_baggage = _CURRENT_BAGGAGE.get() or {}
    cid = (
        correlation_id or current_id() or curr_baggage.get("correlation_id") or new_correlation_id()
    )
    carrier[CORRELATION_HEADER] = cid

    # 3. Merge baggage
    combined_baggage = dict(curr_baggage)
    if baggage:
        combined_baggage.update(baggage)
    combined_baggage["correlation_id"] = cid

    if combined_baggage:
        carrier[W3C_BAGGAGE_HEADER] = format_baggage(combined_baggage)

    return carrier


def extract_context(headers: Mapping[str, str]) -> ExtractedContext:
    """Extracts W3C traceparent, baggage, and correlation context from inbound headers."""
    # Normalize headers to lowercase
    normalized = {k.lower(): v for k, v in headers.items()}

    # Extract OpenTelemetry context
    otel_ctx = _PROPAGATOR.extract(normalized, context=Context())

    # Extract traceparent parts
    tp = normalized.get(W3C_TRACEPARENT_HEADER)
    parsed_tp = parse_traceparent(tp) if tp else None
    trace_id = parsed_tp[1] if parsed_tp else None
    span_id = parsed_tp[2] if parsed_tp else None
    trace_flags = parsed_tp[3] if parsed_tp else None

    # Extract baggage
    raw_baggage = normalized.get(W3C_BAGGAGE_HEADER, "")
    bag_dict = parse_baggage(raw_baggage)

    # Extract correlation ID: check X-Correlation-ID header, then baggage, then generate fresh
    raw_cid = normalized.get(CORRELATION_HEADER.lower()) or bag_dict.get("correlation_id")
    cid = resolve_inbound_id(raw_cid)
    bag_dict["correlation_id"] = cid

    return ExtractedContext(
        trace_id=trace_id,
        span_id=span_id,
        trace_flags=trace_flags,
        correlation_id=cid,
        baggage=bag_dict,
        otel_context=otel_ctx,
    )
