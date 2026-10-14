"""Run one assistant turn on ADK: verified identity in, structured answer out (spec 021 FR-005..008, FR-014, FR-016).

Identity is the `Principal` built from the verified operator; the ADK user id is its uid and the session is per
workstation and entity, so another operator's thread cannot be reached. Every outcome is an `Answer`: a timeout or a
model failure is reported plainly with no figure, never an invented one.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from google.adk.agents.run_config import RunConfig
from google.adk.apps.app import App
from google.adk.models.base_llm import BaseLlm
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService

from eios.assistant.agents import build_agent
from eios.assistant.answer import Answer
from eios.assistant.assembler_agent import (
    ANSWER_METADATA_KEY,
    ATTEMPT_KEY,
    FEEDBACK_KEY,
)
from eios.assistant.config import AssistantConfigError, AssistantSettings
from eios.assistant.sessions import APP_NAME, session_key
from eios.assistant.tools import FACT_IDS_KEY, ORIGINS_KEY, PROPOSALS_KEY, SOURCES_KEY
from eios.llm_gateway.providers.adk_types import user_message
from eios.ontology.omcp.port.facts import FactResolver
from eios.ontology.omcp.port.principal import Principal
from eios.ontology.omcp.port.service import GovernedToolPort

logger = logging.getLogger(__name__)

UNAVAILABLE_TEXT = "I can't answer that right now. Please try again in a moment."
TIMEOUT_TEXT = (
    "That took longer than the time allowed, so I stopped. Please try a narrower question."
)


@dataclass(frozen=True)
class ToolCallTrace:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None
    error_code: str | None


@dataclass(frozen=True)
class TurnOutcome:
    answer: Answer
    tool_calls: tuple[ToolCallTrace, ...] = ()
    steps: tuple[str, ...] = ()  # real progress: the capabilities used, in order (FR-005)
    latency_ms: float = 0.0
    status: str = "ok"  # ok | timeout | error
    error: str | None = None
    model_calls: int = 0
    events: tuple[Any, ...] = field(default=(), repr=False)


def _unavailable(text: str, reason: str) -> Answer:
    return Answer(text=text, fallback_reason=reason)


def _fresh_turn_state(
    entity_id: str | None, entity_context: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        ATTEMPT_KEY: 0,
        FEEDBACK_KEY: "",
        FACT_IDS_KEY: [],
        SOURCES_KEY: [],
        ORIGINS_KEY: [],
        PROPOSALS_KEY: [],
        "entity_id": entity_id,
        "entity_context": entity_context or {},
    }


class AssistantRuntime:
    def __init__(
        self,
        *,
        port: GovernedToolPort,
        facts: FactResolver,
        settings: AssistantSettings,
        session_service: BaseSessionService,
        model: str | BaseLlm | None = None,
        plugins: tuple[BasePlugin, ...] = (),
    ) -> None:
        chosen = model or settings.model
        if chosen is None:
            raise AssistantConfigError(
                "EIOS_GEMINI_MODEL must name the model; no model id lives in source"
            )
        self._port, self._facts, self._settings = port, facts, settings
        self._sessions, self._model, self._plugins = session_service, chosen, plugins

    async def run_turn(
        self,
        *,
        principal: Principal,
        question: str,
        entity_id: str | None = None,
        entity_context: dict[str, Any] | None = None,
    ) -> TurnOutcome:
        started = time.perf_counter()
        try:
            outcome = await asyncio.wait_for(
                self._consume(principal, question, entity_id, entity_context),
                timeout=self._settings.turn_deadline_s,
            )
        except TimeoutError:
            return TurnOutcome(
                _unavailable(TIMEOUT_TEXT, "turn deadline exceeded"),
                latency_ms=_ms(started),
                status="timeout",
                error=f"deadline of {self._settings.turn_deadline_s}s exceeded",
            )
        except (
            Exception
        ) as exc:  # model, data or session failure: report it, never invent an answer
            logger.exception(
                "assistant turn failed for workstation %s", principal.workstation.value
            )
            return TurnOutcome(
                _unavailable(UNAVAILABLE_TEXT, type(exc).__name__),
                latency_ms=_ms(started),
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )
        return TurnOutcome(**{**outcome.__dict__, "latency_ms": _ms(started)})

    async def _consume(
        self,
        principal: Principal,
        question: str,
        entity_id: str | None,
        entity_context: dict[str, Any] | None,
    ) -> TurnOutcome:
        agent = build_agent(
            port=self._port, facts=self._facts, principal=principal, model=self._model
        )
        app = App(name=APP_NAME, root_agent=agent, plugins=list(self._plugins))
        runner = Runner(app=app, session_service=self._sessions, auto_create_session=True)
        offered = {spec.name for spec in self._port.list_tools(principal)}
        answer: Answer | None = None
        calls: dict[str, dict[str, Any]] = {}
        traces: list[ToolCallTrace] = []
        events: list[Any] = []
        async for event in runner.run_async(
            user_id=principal.uid,
            session_id=session_key(principal.workstation.value, entity_id),
            new_message=user_message(question),
            state_delta=_fresh_turn_state(entity_id, entity_context),
            run_config=RunConfig(max_llm_calls=self._settings.max_llm_calls),
        ):
            events.append(event)
            for call in event.get_function_calls():
                calls[call.id or call.name or ""] = {
                    "name": call.name or "",
                    "args": dict(call.args or {}),
                }
            for response in event.get_function_responses():
                traces.append(self._trace(principal, offered, calls, response))
            metadata = event.custom_metadata or {}
            if ANSWER_METADATA_KEY in metadata:
                answer = Answer.model_validate(metadata[ANSWER_METADATA_KEY])
        if answer is None:
            return TurnOutcome(
                _unavailable(UNAVAILABLE_TEXT, "no answer was assembled"),
                tuple(traces),
                status="error",
                error="the assembler produced no answer",
                events=tuple(events),
            )
        return TurnOutcome(
            answer,
            tuple(traces),
            steps=tuple(t.name for t in traces),
            events=tuple(events),
            model_calls=sum(1 for e in events if e.author == "drafter"),
        )

    def _trace(
        self,
        principal: Principal,
        offered: set[str],
        calls: dict[str, dict[str, Any]],
        response: Any,
    ) -> ToolCallTrace:
        issued = calls.get(
            response.id or response.name or "", {"name": response.name or "", "args": {}}
        )
        if issued["name"] not in offered:
            # ADK answered "no such tool" itself. Replay it through the port, which refuses and records it (FR-010).
            refused = self._port.call(principal, issued["name"], issued["args"])
            code = refused.error.code.value if refused.error else "FORBIDDEN_ROLE"
            return ToolCallTrace(issued["name"], issued["args"], None, code)
        payload = dict(response.response or {})
        error = payload.get("error")
        return ToolCallTrace(
            issued["name"],
            issued["args"],
            None if error else payload,
            error.get("code") if isinstance(error, dict) else None,
        )


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
