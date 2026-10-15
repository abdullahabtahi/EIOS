"""Judge the ADK assistant through the agent port (spec 021 FR-019, spec 022 FR-003).

Identity is the verified operator the port is given. Each case gets its own in-memory conversation, so one golden case
never remembers another. Offline, the model is the `RuleLlm`; live, it is the configured model through ADK. Every
figure the assembler placed is bound to the governed result it came from, so the faithfulness judge verifies by value.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import replace
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from eios.agent_gates.adapters.adk_offline import RuleLlm
from eios.agent_gates.adapters.offline_regulations import offline_index
from eios.agent_gates.port import TurnRequest, completed_record, inconclusive_record
from eios.agent_gates.records import (
    Binding,
    DataOrigin,
    FactRef,
    IdentitySource,
    ToolCall,
    ToolErrorCode,
    TurnRecord,
)
from eios.assistant.answer import Answer
from eios.assistant.config import AssistantSettings
from eios.assistant.runtime import AssistantRuntime, ToolCallTrace, TurnOutcome
from eios.dataplane.plane import read_models
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import PortError
from eios.ontology.omcp.port.principal import principal_for
from eios.ontology.omcp.port.service import GovernedToolPort

logger = logging.getLogger(__name__)
REFUSED_IDENTITY = "I cannot answer that from the governed data available to this workstation."
_EVAL_ENVIRONMENT = "test"


class _OverlayPort:
    """Attack fixtures: overlay fields on a real result (same shape, injected text) before the agent sees it."""

    def __init__(self, port: GovernedToolPort, overlays: dict[str, dict[str, Any]]) -> None:
        self._port, self._overlays = port, overlays

    def __getattr__(self, name: str) -> Any:
        return getattr(self._port, name)

    def call(self, principal: Any, tool: str, arguments: dict[str, Any]) -> Any:
        outcome = self._port.call(principal, tool, arguments)
        overlay = (
            self._overlays.get(self._port.spec_for_capability_of(tool).capability)
            if outcome.result
            else None
        )
        if overlay and outcome.result is not None:
            return type(outcome)(
                tool=outcome.tool, result=outcome.result.model_copy(update=overlay)
            )
        return outcome


class AdkRuntime:
    runtime_name = "adk"

    def __init__(self, *, offline: bool = True, model_key: str | None = None) -> None:
        self.offline = offline
        self._model_key = model_key  # a registry key for a live run; None is the registry default
        models = (
            read_models()
        )  # the plane `EIOS_DATA_PLANE` names, so a plane is judged as the cockpit runs it
        if (
            offline and models.knowledge is None
        ):  # the scripted run still exercises retrieval, on labelled test passages
            models = replace(models, knowledge=offline_index())
        self._port = build_port(models)
        self._settings = AssistantSettings.from_env(
            {**_live_env(), "EIOS_ENVIRONMENT": _EVAL_ENVIRONMENT}
        )
        self._model: BaseLlm | None = RuleLlm() if offline else None
        self._conversations: dict[str, InMemorySessionService] = {}

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        try:
            principal = principal_for(request.operator_id, request.role.value)
        except PortError as exc:
            return completed_record(
                request,
                self.runtime_name,
                f"{REFUSED_IDENTITY} ({exc.error.message})",
                identity_source=IdentitySource.VERIFIED_TOKEN,
            )
        port: Any = (
            _OverlayPort(self._port, request.tool_fixtures) if request.tool_fixtures else self._port
        )
        sessions = self._conversations.setdefault(request.session_id, InMemorySessionService())
        runtime = AssistantRuntime(
            port=port,
            settings=self._settings,
            session_service=sessions,
            model=self._model,
        )
        context = request.entity_context or {}
        outcome = asyncio.run(
            runtime.run_turn(
                principal=principal,
                question=request.question,
                entity_id=context.get("entity_id"),
                entity_context=context,
                model_key=self._model_key,
            )
        )
        logger.info("%s", trace_line(request, outcome))
        if outcome.status != "ok":
            return inconclusive_record(
                request,
                self.runtime_name,
                outcome.error or outcome.status,
                latency_ms=outcome.latency_ms,
                rounds=outcome.model_calls,
                tool_calls=[self._tool_call(trace) for trace in outcome.tool_calls],
            )
        return self._record(request, outcome)

    def _record(self, request: TurnRequest, outcome: TurnOutcome) -> TurnRecord:
        calls = [self._tool_call(trace) for trace in outcome.tool_calls]
        answer = outcome.answer
        return completed_record(
            request,
            self.runtime_name,
            answer.text,
            calls,
            identity_source=IdentitySource.VERIFIED_TOKEN,
            bindings=_bindings(answer, calls) or None,
            citations=list(answer.citations),
            data_origin=DataOrigin(answer.data_origin.value),
            is_replay_fallback=answer.is_replay_fallback,
            fallback_reason=answer.fallback_reason,
            audit_verdict=f"blocked:{answer.block_reason}" if answer.blocked else None,
            latency_ms=outcome.latency_ms,
            rounds=max(outcome.model_calls, 1),
        )

    def _tool_call(self, trace: ToolCallTrace) -> ToolCall:
        try:
            capability: str | None = self._port.spec_for_capability_of(trace.name).capability
        except KeyError, PortError:
            capability = None
        return ToolCall(
            name=trace.name,
            capability=capability,
            arguments=trace.arguments,
            result=trace.result,
            error=ToolErrorCode(trace.error_code) if trace.error_code else None,
            untrusted=bool(trace.result and trace.result.get("untrusted")),
        )


def trace_line(request: TurnRequest, outcome: TurnOutcome) -> str:
    """One log line saying where a turn's time went: model calls, the gaps between events, tools, status."""
    stamps = [e.timestamp for e in outcome.events if getattr(e, "timestamp", None)]
    gaps = [round((b - a) * 1000) for a, b in zip(stamps, stamps[1:], strict=False)]
    return (
        f"turn {request.case_id or request.session_id}.{request.repeat} {outcome.status} "
        f"{outcome.latency_ms:.0f} ms, {outcome.model_calls} model calls, "
        f"tools={[t.name for t in outcome.tool_calls]}, attempts={outcome.answer.attempts}, "
        f"event_gaps_ms={gaps}"
    )


def _live_env() -> dict[str, str]:
    import os

    return {k: v for k, v in os.environ.items() if k.startswith(("EIOS_GEMINI", "EIOS_ASSISTANT_"))}


def _standalone(text: str) -> str:
    """The figure's text, not inside a longer number (0.8 must not match within 0.8044)."""
    return rf"(?<![\d.,]){re.escape(text)}(?![\d]|[.,]\d)"


def _bindings(answer: Answer, calls: list[ToolCall]) -> list[Binding]:
    """Bind each figure the assembler placed to the exact result that returned its fact id."""
    out: list[Binding] = []
    for figure in answer.figures:
        path = figure.fact_id.rsplit(":", 1)[1]
        index = next(
            (
                i
                for i, call in enumerate(calls)
                if call.result and (call.result.get("fact_ids") or {}).get(path) == figure.fact_id
            ),
            None,
        )
        if index is None:
            continue
        for match in re.finditer(_standalone(figure.text), answer.text):
            span = (match.start(), match.end())
            out.append(
                Binding(
                    span=span, fact_ref=FactRef(tool_call_index=index, path=path), unit=figure.unit
                )
            )
    return out
