"""A real turn feeds the operations board's agent objectives; an outage is spent budget, never silence."""

import asyncio

from eios.assistant.answer import Answer
from eios.assistant.runtime import TurnOutcome
from eios.assistant.scripted_model import call, draft
from eios.assistant.telemetry import record_turn
from eios.observability.slo_catalog import SLICategory
from eios.observability.slo_engine import SLOMonitoringEngine
from eios.ontology.omcp.port.principal import principal_for

from .conftest import make_runtime


def _row(engine: SLOMonitoringEngine, sli: SLICategory):
    return next(s for s in engine.evaluate_all_slos() if s.sli_name == sli)


def test_an_answered_turn_counts_for_latency_and_for_the_gate() -> None:
    engine = SLOMonitoringEngine()
    runtime, _ = make_runtime(
        [
            call("get_aml_dossier", entity_id="CR84920"),
            draft("It is {{fact:aml.dossier:CR84920:discrepancy_multiplier}}."),
        ]
    )
    out = asyncio.run(
        runtime.run_turn(
            principal=principal_for("alice", "aml_investigator"),
            question="What is the discrepancy?",
            entity_id="CR84920",
        )
    )
    record_turn(engine, out)
    assert _row(engine, SLICategory.AGENT_TURN_FULL_ANSWER).total_events == 1
    assert _row(engine, SLICategory.HALLUCINATION_GATE).total_events == 1


def test_a_timed_out_turn_spends_latency_budget_and_never_counts_as_passing_the_gate() -> None:
    engine = SLOMonitoringEngine()
    timed_out = TurnOutcome(
        Answer(text="x", fallback_reason="turn deadline exceeded"),
        latency_ms=30000.0,
        status="timeout",
    )
    record_turn(engine, timed_out)
    latency = _row(engine, SLICategory.AGENT_TURN_FULL_ANSWER)
    assert latency.total_events == 1
    assert latency.budget_remaining_pct < 100.0
    assert _row(engine, SLICategory.HALLUCINATION_GATE).total_events == 0


def test_the_first_token_objective_stays_unobserved_because_nothing_streams() -> None:
    engine = SLOMonitoringEngine()
    record_turn(engine, TurnOutcome(Answer(text="ok"), latency_ms=1500.0))
    assert _row(engine, SLICategory.AGENT_TURN_FIRST_TOKEN).total_events == 0


def test_recording_never_breaks_a_turn() -> None:
    record_turn(None, TurnOutcome(Answer(text="ok"), latency_ms=1.0))  # type: ignore[arg-type]
