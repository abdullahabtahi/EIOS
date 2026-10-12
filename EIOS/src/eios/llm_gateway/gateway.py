"""The provider-neutral LLM gateway: ``Gateway.complete`` is the single access point (FR-021).

Flow per call: resolve the locked prompt, render it, derive the replay key, check the daily cap,
call the provider only if allowed, degrade to a cached replay or an explicit ``unavailable``
on failure, then write exactly one redacted trace. Nothing here computes a business metric and
nothing invents text: a response is provider output, a stored earlier output, or no text.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from eios.common.logging_redaction import redact_exception
from eios.llm_gateway.caps import (
    CapEvent,
    CounterStore,
    EventSink,
    crossing_events,
    is_exhausted,
    refusal_event,
    usage_day,
)
from eios.llm_gateway.config import GatewayConfig, config_identity
from eios.llm_gateway.models import CallMeasure, GatewayRequest, GatewayResponse, Outcome
from eios.llm_gateway.prompt_lock import PromptLock
from eios.llm_gateway.providers.base import (
    Provider,
    ProviderOutputInvalid,
    ProviderResult,
    ProviderUnavailable,
    parse_provider_result,
)
from eios.llm_gateway.render import render_prompt
from eios.llm_gateway.replay_cache import ReplayStore, StoredReplay, replay_key
from eios.llm_gateway.trace import TraceSink, build_trace, measure_call

_LOG = logging.getLogger("eios.llm_gateway")
_MILLISECOND = timedelta(milliseconds=1)
_NO_USAGE = (0, 0)


class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True)
class GatewayStores:
    counter: CounterStore
    replay: ReplayStore


@dataclass(frozen=True)
class GatewaySinks:
    trace: TraceSink
    events: EventSink


@dataclass(frozen=True)
class _Attempt:
    """What happened to one call, before it is turned into a response and a trace."""

    outcome: Outcome
    content: str | None = None
    replay: StoredReplay | None = None
    tokens: tuple[int, int] = _NO_USAGE


class Gateway:
    """Configuration, provider and stores are injected; there is no default model or provider."""

    def __init__(
        self,
        config: GatewayConfig,
        provider: Provider,
        stores: GatewayStores,
        prompts: PromptLock,
        sinks: GatewaySinks,
        clock: Clock,
        new_id: Callable[[], str],
    ) -> None:
        self._config = config
        self._identity = config_identity(config)
        self._provider = provider
        self._stores = stores
        self._prompts = prompts
        self._sinks = sinks
        self._clock = clock
        self._new_id = new_id

    def complete(self, request: GatewayRequest) -> GatewayResponse:
        """Run one request. Prompt, template and input errors raise before any provider call."""
        started = self._clock.now()
        locked = self._prompts.resolve(request.prompt_id, request.prompt_version)
        rendered = render_prompt(locked.template, request.inputs)
        key = replay_key(
            prompt_id=request.prompt_id,
            prompt_version=request.prompt_version,
            inputs=request.inputs,
            config_identity=self._identity,
        )
        attempt = self._attempt(rendered, key, started)
        return self._finish(request, attempt, started)

    def _attempt(self, rendered: str, key: str, started: datetime) -> _Attempt:
        day = usage_day(started)
        used = self._stores.counter.add_tokens(day, 0)
        cap = self._config.daily_token_cap
        if is_exhausted(used, cap):
            cached = self._stores.replay.get(key)
            if cached is not None:
                return _Attempt(Outcome.REPLAY, cached.content, cached)
            self._sinks.events.emit(refusal_event(day, used=used, cap=cap))
            return _Attempt(Outcome.CAP_REACHED)
        return self._call_provider(rendered, key, started, used)

    def _call_provider(self, rendered: str, key: str, started: datetime, used: int) -> _Attempt:
        try:
            result = parse_provider_result(
                self._provider.generate(rendered, self._config.model_id, self._config.rate_limits)
            )
        except (ProviderUnavailable, ProviderOutputInvalid) as exc:
            _LOG.warning("provider call failed: %s", redact_exception(exc))
            cached = self._stores.replay.get(key)
            if cached is not None:
                return _Attempt(Outcome.REPLAY, cached.content, cached)
            return _Attempt(Outcome.UNAVAILABLE)
        return self._record_success(result, key, started, used)

    def _record_success(
        self, result: ProviderResult, key: str, started: datetime, used: int
    ) -> _Attempt:
        day = usage_day(started)
        after = self._stores.counter.add_tokens(day, result.tokens_in + result.tokens_out)
        for event in crossing_events(
            day,
            before=used,
            after=after,
            cap=self._config.daily_token_cap,
            thresholds=self._config.cap_warning_thresholds_percent,
        ):
            self._emit_event(event)
        self._stores.replay.put(key, result.content, self._clock.now())
        return _Attempt(Outcome.OK, result.content, None, (result.tokens_in, result.tokens_out))

    def _emit_event(self, event: CapEvent) -> None:
        self._sinks.events.emit(event)

    def _finish(
        self, request: GatewayRequest, attempt: _Attempt, started: datetime
    ) -> GatewayResponse:
        ended = self._clock.now()
        measure = measure_call(
            self._config,
            tokens_in=attempt.tokens[0],
            tokens_out=attempt.tokens[1],
            latency_ms=max(0, (ended - started) // _MILLISECOND),
        )
        return self._emit_trace(request, attempt, measure, ended)

    def _emit_trace(
        self, request: GatewayRequest, attempt: _Attempt, measure: CallMeasure, ended: datetime
    ) -> GatewayResponse:
        original_at = attempt.replay.stored_at if attempt.replay is not None else None
        trace = build_trace(
            trace_id=self._new_id(),
            request=request,
            config_identity=self._identity,
            measure=measure,
            outcome=attempt.outcome,
            replay_original_at=original_at,
            recorded_at=ended,
        )
        self._sinks.trace.emit(trace.to_record())
        return GatewayResponse(
            outcome=attempt.outcome,
            content=attempt.content,
            trace_id=trace.trace_id,
            replay_original_at=original_at,
        )
