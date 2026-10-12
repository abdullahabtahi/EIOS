"""LLM call traces (FR-026): one schema-valid, redacted record per call, whatever the outcome.

Traces carry identifiers, token counts, cost, latency and outcome only. Cost is derived from
configured prices and is null when none are configured; it is never estimated.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from eios.common.logging_redaction import redact_text
from eios.llm_gateway.config import GatewayConfig
from eios.llm_gateway.models import CallMeasure, GatewayRequest, LLMCallTrace, Outcome


class TraceSink(Protocol):
    def emit(self, record: Mapping[str, object]) -> None: ...


def measure_call(
    config: GatewayConfig, *, tokens_in: int, tokens_out: int, latency_ms: int
) -> CallMeasure:
    """Token, latency and cost figures for one call; cost comes only from configured prices."""
    prices = config.prices
    cost = None if prices is None else prices.cost(tokens_in=tokens_in, tokens_out=tokens_out)
    return CallMeasure(tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms, cost=cost)


def build_trace(
    *,
    trace_id: str,
    request: GatewayRequest,
    config_identity: str,
    measure: CallMeasure,
    outcome: Outcome,
    replay_original_at: datetime | None,
    recorded_at: datetime,
) -> LLMCallTrace:
    """Assemble a trace; the correlation id is redacted because callers supply it."""
    return LLMCallTrace(
        trace_id=trace_id,
        correlation_id=redact_text(request.correlation_id),
        prompt_id=request.prompt_id,
        prompt_version=request.prompt_version,
        config_identity=config_identity,
        tokens_in=measure.tokens_in,
        tokens_out=measure.tokens_out,
        cost=measure.cost,
        latency_ms=measure.latency_ms,
        outcome=outcome,
        replay_original_at=replay_original_at,
        recorded_at=recorded_at,
    )
