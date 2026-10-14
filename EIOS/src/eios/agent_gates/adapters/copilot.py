"""Today's copilot behind the AgentPort (spec 022, research R-4).

`CopilotEngine.process_query` returns only a count and an evidence ledger, not what each tool was called with
or returned, and it has two paths (a live model loop and a hard-coded replay) that call tools differently.
For the duration of one turn this adapter wraps every tool the engine can reach, in both its tool table and
its module namespace, records each call, and applies tool fixtures. A staged recommendation is recorded as a
proposal call so the judges see it. The copilot takes its role from the caller and has no entity-context
parameter; the record says so (`identity_source = request_body`).
"""

import inspect
import threading
import time
from collections.abc import Callable
from contextlib import ExitStack
from typing import Any, cast
from unittest import mock

import eios.conversation.copilot_engine as engine_module
from eios.agent_gates.capabilities import default_map
from eios.agent_gates.port import TurnRequest, completed_record
from eios.agent_gates.records import DataOrigin, IdentitySource, ToolCall, ToolErrorCode, TurnRecord
from eios.conversation.copilot_engine import CopilotEngine
from eios.conversation.models import OperatorRole

UNTRUSTED_CAPABILITIES = frozenset({"partner.comms", "knowledge.regulation", "knowledge.policy"})
_LOCK = threading.Lock()  # tool wrapping patches module globals, so turns run one at a time


def _recorder(
    name: str, func: Callable[..., Any], calls: list[ToolCall], fixtures: dict[str, dict[str, Any]]
) -> Callable[..., Any]:
    capability = default_map().capability_for_tool("copilot", name)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        arguments = dict(inspect.signature(func).bind(*args, **kwargs).arguments)
        started = time.perf_counter()
        fixture = fixtures.get(capability) if capability else None
        error: ToolErrorCode | None = None
        try:
            result = func(*args, **kwargs)
            if (
                fixture is not None
            ):  # overlay: injected text rides on a real result so the tool keeps its shape
                result = {**(result if isinstance(result, dict) else {}), **fixture}
        except Exception:
            error, result = ToolErrorCode.OTHER, None
            raise
        finally:
            calls.append(
                ToolCall(
                    name=name,
                    capability=capability,
                    arguments=arguments,
                    result=result
                    if isinstance(result, dict)
                    else ({"result": result} if error is None else None),
                    error=error,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    untrusted=capability in UNTRUSTED_CAPABILITIES,
                )
            )
        return result

    return wrapper


def _data_origin(calls: list[ToolCall]) -> DataOrigin:
    origins = [
        str(c.result.get("data_origin", "")).lower()
        for c in calls
        if c.result and "data_origin" in c.result
    ]
    return DataOrigin.LIVE if origins and all("live" in o for o in origins) else DataOrigin.FIXTURE


class CopilotAdapter:
    runtime_name = "copilot"

    def __init__(self, engine: CopilotEngine | None = None, offline: bool = True) -> None:
        self.engine = engine or CopilotEngine(offline_mode=offline)

    def run_turn(self, request: TurnRequest) -> TurnRecord:
        calls: list[ToolCall] = []
        wrapped: dict[str, Callable[..., Any]] = {
            n: _recorder(n, cast("Callable[..., Any]", f), calls, request.tool_fixtures)
            for n, f in engine_module.TOOL_MAP.items()
        }
        with _LOCK, ExitStack() as stack:
            stack.enter_context(mock.patch.dict(engine_module.TOOL_MAP, wrapped))
            for name, wrapper in wrapped.items():
                if hasattr(engine_module, name):
                    stack.enter_context(mock.patch.object(engine_module, name, wrapper))
            response = self.engine.process_query(
                query=request.question,
                role=OperatorRole(request.role.value),
                session_id=request.session_id,
                turn_index=request.turn_index,
            )
        staged = response.staged_recommendation
        if staged:
            calls.append(
                ToolCall(
                    name="staged_recommendation",
                    capability="action.propose_hold",
                    arguments={k: staged.get(k) for k in ("action_type", "target_entity_id")},
                    result=dict(staged),
                )
            )
        return completed_record(
            request,
            self.runtime_name,
            response.response_markdown,
            calls,
            identity_source=IdentitySource.REQUEST_BODY,
            rounds=1 + int(response.reflection_cycles_used),
            citations=list(response.citations),
            is_replay_fallback=response.is_replay_fallback,
            fallback_reason=(response.fallback_reason or "deterministic grounded replay")
            if response.is_replay_fallback
            else None,
            audit_verdict=response.auditor_status,
            data_origin=_data_origin(calls),
            latency_ms=float(response.turn_latency_ms),
        )
