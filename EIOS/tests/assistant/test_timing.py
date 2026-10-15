"""A turn says where its time went: model calls and tool calls timed where they happen."""

import asyncio

from eios.assistant.scripted_model import call, draft
from eios.assistant.timing import TurnTimer
from eios.ontology.omcp.port.principal import principal_for

from .conftest import make_runtime


def test_the_breakdown_never_goes_negative_and_keeps_each_model_call() -> None:
    timer = TurnTimer(model_calls_ms=[400.0, 600.0], tool_calls_ms=[50.0])
    assert timer.breakdown(2000.0) == {
        "model": 1000.0,
        "tools": 50.0,
        "other": 950.0,
        "model_calls": [400.0, 600.0],
    }
    assert timer.breakdown(10.0)["other"] == 0.0


def test_a_real_turn_reports_its_model_and_tool_time() -> None:
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
    assert len(out.timing["model_calls"]) == out.model_calls == 2
    assert out.timing["tools"] > 0
    assert out.timing["model"] + out.timing["tools"] + out.timing["other"] >= out.latency_ms - 1
