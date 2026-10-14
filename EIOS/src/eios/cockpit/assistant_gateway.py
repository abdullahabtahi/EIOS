"""Serve the copilot endpoint from the ADK assistant when `EIOS_ASSISTANT_RUNTIME=adk` (spec 021 FR-017).

The default stays `legacy` until the assistant has beaten the baseline through the agent gates. The response keeps the
shape the browser reads today and adds the structured fields (figures, proposals, steps, blocked). A model, data or
session failure is reported as such: it is labelled and carries no invented figure.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from typing import Any

from eios.assistant.answer import Answer
from eios.assistant.config import AssistantConfigError, AssistantSettings
from eios.assistant.runtime import AssistantRuntime, TurnOutcome
from eios.assistant.safety import build_safety_plugins
from eios.assistant.sessions import build_session_service
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.readmodels import ReadModels

RUNTIME_ENV = "EIOS_ASSISTANT_RUNTIME"
RUNTIMES = frozenset({"legacy", "adk"})

_lock = threading.Lock()
_runtime: AssistantRuntime | None = None


def assistant_enabled(env: Mapping[str, str] | None = None) -> bool:
    chosen = (os.environ if env is None else env).get(RUNTIME_ENV, "legacy").strip().lower()
    if chosen not in RUNTIMES:
        raise AssistantConfigError(
            f"{RUNTIME_ENV} must be one of {sorted(RUNTIMES)}, not '{chosen}'"
        )
    return chosen == "adk"


def get_runtime() -> AssistantRuntime:
    """Built on first use from the environment; a deployed environment without its safeguards refuses here."""
    global _runtime
    with _lock:
        if _runtime is None:
            settings = AssistantSettings.from_env()
            _runtime = AssistantRuntime(
                port=build_port(ReadModels.default()),
                settings=settings,
                session_service=build_session_service(settings),
                plugins=build_safety_plugins(settings),
            )
        return _runtime


def set_runtime_for_testing(runtime: AssistantRuntime | None) -> None:
    global _runtime
    with _lock:
        _runtime = runtime


def _auditor_status(answer: Answer) -> str:
    if answer.blocked:
        return "BLOCKED"
    if answer.failed_closed or answer.fallback_reason:
        return "UNAUDITED"
    return "PASS"


def response_body(query: str, outcome: TurnOutcome) -> dict[str, Any]:
    answer = outcome.answer
    return {
        "query": query,
        "response": answer.text,
        "auditor_status": _auditor_status(answer),
        "is_replay_fallback": answer.is_replay_fallback,
        "fallback_reason": answer.fallback_reason,
        "provenance_citations": [
            {
                "metric_id": figure.fact_id,
                "formatted_value": figure.text,
                "steward": figure.fact_id.split(":", 1)[0],
                "as_of": figure.as_of.isoformat(),
            }
            for figure in answer.figures
        ],
        "audit_record": {
            "passed": _auditor_status(answer) == "PASS",
            "unanchored_tokens": [],
            "anchored_numbers": [figure.text for figure in answer.figures],
            "relative_tolerance": 0.0,
        },
        "tool_trace_count": len(outcome.tool_calls),
        "suggested_action": answer.proposed_actions[0] if answer.proposed_actions else None,
        "turn_latency_ms": outcome.latency_ms,
        "blocked": answer.blocked,
        "block_reason": answer.block_reason,
        "steps": list(outcome.steps),
        "proposed_actions": list(answer.proposed_actions),
        "data_origin": answer.data_origin.value,
    }
