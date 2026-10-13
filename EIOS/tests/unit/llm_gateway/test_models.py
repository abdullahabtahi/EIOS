"""T111: gateway models are frozen and enforce the response/trace invariants."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from eios.common.untrusted_text import wrap_untrusted
from eios.common.validation import StrictModel
from eios.llm_gateway.models import (
    CallMeasure,
    GatewayRequest,
    GatewayResponse,
    LLMCallTrace,
    Outcome,
)

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _trace(**overrides: object) -> LLMCallTrace:
    fields: dict[str, object] = {
        "trace_id": "t-1",
        "correlation_id": "c-1",
        "prompt_id": "smoke-echo",
        "prompt_version": "v1",
        "config_identity": "abc",
        "tokens_in": 1,
        "tokens_out": 2,
        "cost": 0.5,
        "latency_ms": 3,
        "outcome": Outcome.OK,
        "recorded_at": NOW,
    }
    return LLMCallTrace(**{**fields, **overrides})  # type: ignore[arg-type]


def _request() -> GatewayRequest:
    return GatewayRequest(
        prompt_id="smoke-echo",
        prompt_version="v1",
        inputs={"message": "hi"},
        correlation_id="c-1",
        caller="svc",
    )


def test_outcome_vocabulary_is_exactly_four() -> None:
    assert {o.value for o in Outcome} == {"ok", "replay", "unavailable", "cap_reached"}


@pytest.mark.parametrize("model", [GatewayRequest, GatewayResponse, LLMCallTrace, CallMeasure])
def test_every_model_is_frozen_and_forbids_extras(model: type[StrictModel]) -> None:
    assert model.model_config["frozen"] is True
    assert model.model_config["extra"] == "forbid"


def test_instances_reject_assignment() -> None:
    with pytest.raises(ValidationError):
        _trace().tokens_in = 9
    with pytest.raises(ValidationError):
        _request().caller = "other"


def test_request_inputs_cannot_be_mutated() -> None:
    request = _request()
    with pytest.raises(TypeError):
        request.inputs["message"] = "changed"  # type: ignore[index]


def test_request_does_not_alias_the_callers_dict() -> None:
    source = {"message": "hi"}
    request = GatewayRequest(
        prompt_id="p", prompt_version="v1", inputs=source, correlation_id="c", caller="s"
    )
    source["message"] = "changed"
    assert request.inputs["message"] == "hi"


@pytest.mark.parametrize("outcome", [Outcome.OK, Outcome.REPLAY])
def test_content_required_for_ok_and_replay(outcome: Outcome) -> None:
    original = NOW if outcome is Outcome.REPLAY else None
    with pytest.raises(ValidationError):
        GatewayResponse(outcome=outcome, content=None, trace_id="t", replay_original_at=original)
    ok = GatewayResponse(outcome=outcome, content="text", trace_id="t", replay_original_at=original)
    assert ok.content == "text"


@pytest.mark.parametrize("outcome", [Outcome.UNAVAILABLE, Outcome.CAP_REACHED])
def test_content_must_be_null_for_other_outcomes(outcome: Outcome) -> None:
    with pytest.raises(ValidationError):
        GatewayResponse(outcome=outcome, content="invented", trace_id="t")
    assert GatewayResponse(outcome=outcome, content=None, trace_id="t").content is None


def test_replay_original_at_only_for_replay() -> None:
    with pytest.raises(ValidationError):
        GatewayResponse(outcome=Outcome.REPLAY, content="x", trace_id="t")
    with pytest.raises(ValidationError):
        GatewayResponse(outcome=Outcome.OK, content="x", trace_id="t", replay_original_at=NOW)
    replay = GatewayResponse(
        outcome=Outcome.REPLAY, content="x", trace_id="t", replay_original_at=NOW
    )
    assert replay.replay_original_at == NOW


def test_replay_original_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError):
        GatewayResponse(
            outcome=Outcome.REPLAY,
            content="x",
            trace_id="t",
            replay_original_at=datetime(2026, 1, 1),
        )


@pytest.mark.parametrize("trace_id", ["", None])
def test_trace_id_always_present(trace_id: object) -> None:
    with pytest.raises(ValidationError):
        GatewayResponse(outcome=Outcome.UNAVAILABLE, content=None, trace_id=trace_id)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        _trace(trace_id=trace_id)


@pytest.mark.parametrize("field", ["tokens_in", "tokens_out", "latency_ms"])
def test_counts_and_latency_are_non_negative_integers(field: str) -> None:
    with pytest.raises(ValidationError):
        _trace(**{field: -1})
    with pytest.raises(ValidationError):
        _trace(**{field: 1.5})
    assert _trace(**{field: 0}).model_dump()[field] == 0


@pytest.mark.parametrize("bad", [-0.01, float("nan"), float("inf")])
def test_trace_cost_is_null_or_a_finite_non_negative_number(bad: float) -> None:
    with pytest.raises(ValidationError):
        _trace(cost=bad)
    assert _trace(cost=None).cost is None


def test_trace_replay_original_at_follows_outcome() -> None:
    with pytest.raises(ValidationError):
        _trace(outcome=Outcome.REPLAY)
    with pytest.raises(ValidationError):
        _trace(outcome=Outcome.OK, replay_original_at=NOW)
    assert _trace(outcome=Outcome.REPLAY, replay_original_at=NOW).replay_original_at == NOW


def test_trace_record_omits_replay_original_at_unless_replay() -> None:
    assert "replay_original_at" not in _trace().to_record()
    replay = _trace(outcome=Outcome.REPLAY, replay_original_at=NOW).to_record()
    assert replay["replay_original_at"] == "2026-01-01T12:00:00Z"
    assert replay["outcome"] == "replay"


def test_call_measure_validates_counts() -> None:
    with pytest.raises(ValidationError):
        CallMeasure(tokens_in=-1, tokens_out=0, latency_ms=0, cost=None)
    assert CallMeasure(tokens_in=1, tokens_out=2, latency_ms=3, cost=None).tokens_out == 2


def test_request_has_exactly_the_five_contract_fields() -> None:
    assert set(GatewayRequest.model_fields) == {
        "prompt_id",
        "prompt_version",
        "inputs",
        "correlation_id",
        "caller",
    }


def test_request_accepts_wrapped_untrusted_values() -> None:
    wrapped = wrap_untrusted("raw", source="ticket")
    request = GatewayRequest(
        prompt_id="p",
        prompt_version="v1",
        inputs={"body": wrapped},
        correlation_id="c",
        caller="s",
    )
    assert request.inputs["body"] is wrapped


def test_response_has_no_guess_or_numeric_claim_field() -> None:
    names = set(GatewayResponse.model_fields)
    assert names == {"outcome", "content", "trace_id", "replay_original_at"}
