"""Turn outcomes into service-level events, so the operations board's agent objectives read real turns, not NO_DATA.

Two objectives are fed here, from every turn the runtime actually ran:

- `agent_turn_full_answer`: the turn's wall time against the catalogue target. A turn that timed out or failed counts as
  not compliant, so an outage shows as budget spent, never as silence.
- `hallucination_gate`: one event per turn that reached the assembler, observed value 0 (no unverified figure got past it),
  compliant unless a figure was shown without a governed source. That is true by construction of the assembler, so the
  event count is what carries information: how many turns went through the gate, with the draft attempts it took.

`agent_turn_first_token` stays `NO_DATA` on purpose: the assistant does not stream, so there is no first token to time.
The window is this instance's memory since it started, not history. Recording never raises into a turn.
"""

from __future__ import annotations

import logging
import uuid

from eios.assistant.runtime import TurnOutcome
from eios.observability.slo_catalog import DEFAULT_SLO_CATALOG, SLICategory
from eios.observability.slo_engine import SLOMonitoringEngine

_LOG = logging.getLogger(__name__)
_SOURCE = "assistant-runtime"


def record_turn(engine: SLOMonitoringEngine, outcome: TurnOutcome) -> None:
    try:
        turn_id = f"turn-{uuid.uuid4().hex[:8]}"
        seconds = outcome.latency_ms / 1000.0
        target = DEFAULT_SLO_CATALOG[SLICategory.AGENT_TURN_FULL_ANSWER].target_threshold
        engine.record_event(
            SLICategory.AGENT_TURN_FULL_ANSWER,
            seconds,
            target,
            outcome.status == "ok" and seconds <= target,
            turn_id,
            _SOURCE,
            attributes={"status": outcome.status, "model": outcome.model_key},
        )
        if outcome.status == "ok":
            gate = DEFAULT_SLO_CATALOG[SLICategory.HALLUCINATION_GATE].target_threshold
            engine.record_event(
                SLICategory.HALLUCINATION_GATE,
                0.0,
                gate,
                True,
                turn_id,
                _SOURCE,
                attributes={"attempts": outcome.answer.attempts},
            )
    except Exception:
        _LOG.warning("turn telemetry was not recorded", exc_info=True)
