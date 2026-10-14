"""Serve the copilot endpoint from the ADK assistant unless `EIOS_ASSISTANT_RUNTIME=legacy` (spec 021 FR-017).

The default is `adk`; `legacy` stays only until the legacy copilot is deleted. The response keeps the
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
    chosen = (os.environ if env is None else env).get(RUNTIME_ENV, "adk").strip().lower()
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


def assistant_status(answer: Answer) -> str:
    """What the operator should be told about this answer, apart from the legacy auditor vocabulary.

    ASSEMBLED: every figure was filled in by the system from a governed result of this turn.
    BLOCKED: screening stopped the question or the answer (`block_reason` says which).
    FAILED_CLOSED: the assistant could not support an answer, so it showed no figure at all.
    UNAVAILABLE: the model or data failed; nothing was invented.
    """
    if answer.blocked:
        return "BLOCKED"
    if answer.failed_closed:
        return "FAILED_CLOSED"
    if answer.fallback_reason:
        return "UNAVAILABLE"
    return "ASSEMBLED"


_PROPOSAL_FIELDS = (
    "proposal_ref",
    "kind",
    "label",
    "offer",
    "estimated_cost_usd",
    "expected_effect_low",
    "expected_effect_high",
    "expected_effect_basis",
    "approval_requirement",
    "signed",
    "staged",
    "next_step",
    "as_of",
    "data_origin",
    "source",
    "stage_request",
)


def _proposal_view(raw: Mapping[str, Any]) -> dict[str, Any]:
    """The proposal as the browser needs it: what is offered, what it costs, how it is approved, how to stage it."""
    return {name: raw[name] for name in _PROPOSAL_FIELDS if name in raw}


def _auditor_status(answer: Answer) -> str:
    """The Metric Auditor Gate does not run on this path, so this never says PASS; ASSEMBLED means every figure was
    inserted by the system from a governed result of this turn (spec 021 FR-001)."""
    if answer.blocked:
        return "BLOCKED"
    if answer.failed_closed or answer.fallback_reason:
        return "UNAUDITED"
    return "ASSEMBLED"


def response_body(query: str, outcome: TurnOutcome) -> dict[str, Any]:
    answer = outcome.answer
    return {
        "query": query,
        "response": answer.text,
        "auditor_status": _auditor_status(answer),
        "assistant_status": assistant_status(answer),
        "failed_closed": answer.failed_closed,
        "is_replay_fallback": answer.is_replay_fallback,
        "fallback_reason": answer.fallback_reason,
        "provenance_citations": [
            {
                "metric_id": figure.fact_id,
                "formatted_value": figure.text,
                "steward": figure.source,
                "source": figure.source,
                "unit": figure.unit,
                "raw_value": figure.value,
                "data_origin": figure.data_origin.value,
                "as_of": figure.as_of.isoformat(),
            }
            for figure in answer.figures
        ],
        "audit_record": {
            "passed": False,  # the Metric Auditor Gate did not run; see `verification`
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
        "proposals": [_proposal_view(p) for p in answer.proposed_actions],
        "data_origin": answer.data_origin.value,
        "verification": {
            "method": "assembled_from_governed_results",
            "passed": _auditor_status(answer) == "ASSEMBLED",
            "figures": len(answer.figures),
        },
    }
