"""Serve the copilot endpoint from the ADK assistant (spec 021 FR-017).

The ADK assistant is the only runtime. The response keeps the
shape the browser reads today and adds the structured fields (figures, proposals, steps, blocked). A model, data or
session failure is reported as such: it is labelled and carries no invented figure.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Mapping
from typing import Any

from eios.assistant.answer import Answer
from eios.assistant.config import AssistantSettings
from eios.assistant.runtime import AssistantRuntime, TurnOutcome
from eios.assistant.safety import build_safety_plugins
from eios.assistant.sessions import build_session_service
from eios.dataplane.plane import read_models
from eios.ontology.omcp.port.catalogue import build_port

_LOG = logging.getLogger(__name__)
_lock = threading.Lock()
_runtime: AssistantRuntime | None = None


def get_runtime() -> AssistantRuntime:
    """Built on first use from the environment; a deployed environment without its safeguards refuses here."""
    global _runtime
    with _lock:
        if _runtime is None:
            settings = AssistantSettings.from_env()
            _runtime = AssistantRuntime(
                port=build_port(read_models()),
                settings=settings,
                session_service=build_session_service(settings),
                plugins=build_safety_plugins(settings),
            )
        return _runtime


async def warm_up() -> None:
    """Build the runtime and open its connections at startup, so the first operator does not pay for it.

    Best effort: a missing configuration or an unreachable service is logged, never raised. The first real turn
    reports its own failure (503 offline), so a warm-up that cannot run changes nothing about honesty."""
    try:
        runtime = await asyncio.to_thread(get_runtime)
        await runtime.warm_up()
    except Exception:
        _LOG.warning("assistant warm-up skipped", exc_info=True)


SHUTDOWN_DRAIN_S = 8.0  # Cloud Run gives a stopping instance 10 s after SIGTERM


async def drain_sessions(timeout_s: float = SHUTDOWN_DRAIN_S) -> None:
    """Write the conversation events still held in memory before the process exits (write-behind sessions)."""
    runtime = _runtime
    if runtime is None:
        return
    try:
        await asyncio.wait_for(runtime.flush(), timeout=timeout_s)
    except TimeoutError:
        _LOG.error("assistant sessions: some events were not written before shutdown")
    except Exception:
        _LOG.exception("assistant sessions could not be drained at shutdown")


def set_runtime_for_testing(runtime: AssistantRuntime | None) -> None:
    global _runtime
    with _lock:
        _runtime = runtime


def assistant_status(answer: Answer) -> str:
    """What the operator should be told about this answer.

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


def response_body(query: str, outcome: TurnOutcome) -> dict[str, Any]:
    answer = outcome.answer
    return {
        "query": query,
        "response": answer.text,
        "assistant_status": assistant_status(answer),
        "failed_closed": answer.failed_closed,
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
        "sources": [
            {
                "passage_id": source.passage_id,
                "document_id": source.document_id,
                "title": source.title,
                "jurisdiction": source.jurisdiction,
                "pages": source.pages,
                "text": source.text,
                "data_origin": source.data_origin.value,
            }
            for source in answer.sources
        ],
        "turn_latency_ms": outcome.latency_ms,
        "model": outcome.model_key,
        "timing_ms": outcome.timing,
        "blocked": answer.blocked,
        "block_reason": answer.block_reason,
        "steps": list(outcome.steps),
        "proposals": [_proposal_view(p) for p in answer.proposed_actions],
        "data_origin": answer.data_origin.value,
        "verification": {
            "method": "assembled_from_governed_results",
            "passed": assistant_status(answer) == "ASSEMBLED",
            "figures": len(answer.figures),
        },
    }
