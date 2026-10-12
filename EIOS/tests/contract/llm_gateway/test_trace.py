"""T106 (FR-026): one schema-valid, redacted trace per call, whatever the outcome."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from eios.llm_gateway.config import config_identity
from eios.llm_gateway.providers.stub import StubFailure, StubProvider
from tests.support.llm_gateway import (
    FixedUsageProvider,
    MutableClock,
    echo_request,
    make_config,
    make_kit,
)
from tests.support.secret_shapes import all_shapes

REPO = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((REPO / "schemas" / "llm-call-trace.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
TIMESTAMP = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z"


def _drive_every_outcome(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Return (kit, responses) after producing ok, replay, unavailable and cap_reached."""
    kit = make_kit(tmp_path, config=make_config(daily_token_cap=1))
    responses = [kit.gateway.complete(echo_request("same"))]  # ok
    responses.append(kit.gateway.complete(echo_request("same")))  # replay (cap)
    responses.append(kit.gateway.complete(echo_request("new")))  # cap_reached
    kit.clock.advance(timedelta(days=1))
    kit.provider.inner = StubProvider(failure=StubFailure.UNAVAILABLE)
    responses.append(kit.gateway.complete(echo_request("other")))  # unavailable
    return kit, responses


def test_every_outcome_writes_exactly_one_schema_valid_trace(tmp_path: Path) -> None:
    kit, responses = _drive_every_outcome(tmp_path)
    assert [r.outcome.value for r in responses] == ["ok", "replay", "cap_reached", "unavailable"]
    assert [t["outcome"] for t in kit.traces.records] == [r.outcome.value for r in responses]
    for record, response in zip(kit.traces.records, responses, strict=True):
        assert list(VALIDATOR.iter_errors(record)) == []
        assert record["trace_id"] == response.trace_id


def test_trace_ids_are_unique_per_call(tmp_path: Path) -> None:
    kit, _ = _drive_every_outcome(tmp_path)
    ids = [t["trace_id"] for t in kit.traces.records]
    assert len(set(ids)) == len(ids)


def test_trace_carries_prompt_correlation_and_config_identity(tmp_path: Path) -> None:
    kit = make_kit(tmp_path)
    kit.gateway.complete(echo_request(correlation_id="corr-xyz"))
    record = kit.traces.records[0]
    assert record["prompt_id"] == "smoke-echo"
    assert record["prompt_version"] == "v1"
    assert record["correlation_id"] == "corr-xyz"
    assert record["config_identity"] == config_identity(kit.config)
    assert record["recorded_at"] == kit.clock.instant.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_replay_trace_has_original_timestamp_and_other_traces_omit_it(tmp_path: Path) -> None:
    kit, _ = _drive_every_outcome(tmp_path)
    by_outcome = {t["outcome"]: t for t in kit.traces.records}
    assert "replay_original_at" in by_outcome["replay"]
    for outcome in ("ok", "unavailable", "cap_reached"):
        assert "replay_original_at" not in by_outcome[outcome]


def test_cost_is_derived_from_configured_prices_only(tmp_path: Path) -> None:
    prices = {"input_per_unit": 2.0, "output_per_unit": 4.0, "currency": "USD", "unit": "1 tokens"}
    kit = make_kit(
        tmp_path,
        config=make_config(prices=prices),
        provider=FixedUsageProvider(tokens_in=10, tokens_out=5),
    )
    kit.gateway.complete(echo_request())
    record = kit.traces.records[0]
    assert (record["tokens_in"], record["tokens_out"]) == (10, 5)
    assert record["cost"] == pytest.approx(10 * 2.0 + 5 * 4.0)


def test_cost_is_null_when_no_prices_are_configured(tmp_path: Path) -> None:
    from eios.llm_gateway.config import parse_config
    from tests.support.llm_gateway import config_dict

    data = config_dict()
    data.pop("prices")
    data["verification"].pop("prices")  # type: ignore[attr-defined]
    kit = make_kit(tmp_path, config=parse_config(data, source="test"))
    kit.gateway.complete(echo_request())
    assert kit.traces.records[0]["cost"] is None
    assert list(VALIDATOR.iter_errors(kit.traces.records[0])) == []


def test_calls_that_never_reach_the_provider_cost_nothing_when_priced(tmp_path: Path) -> None:
    kit, _ = _drive_every_outcome(tmp_path)
    by_outcome = {t["outcome"]: t for t in kit.traces.records}
    for outcome in ("replay", "cap_reached", "unavailable"):
        assert by_outcome[outcome]["cost"] == 0.0
        assert by_outcome[outcome]["tokens_in"] == 0


def test_latency_is_measured_from_the_clock(tmp_path: Path) -> None:
    clock = MutableClock(step=timedelta(milliseconds=5))
    kit = make_kit(tmp_path, clock=clock)
    kit.gateway.complete(echo_request())
    latency = kit.traces.records[0]["latency_ms"]
    assert isinstance(latency, int)
    assert latency >= 5


@pytest.mark.parametrize("shape", sorted(all_shapes()))
def test_secret_shaped_strings_never_appear_in_any_trace(tmp_path: Path, shape: str) -> None:
    secret = all_shapes()[shape]
    kit = make_kit(tmp_path, provider=FixedUsageProvider(content=f"reply {secret}"))
    kit.gateway.complete(echo_request(f"note {secret}", correlation_id=f"corr-{secret}"))
    kit.provider.inner = StubProvider(failure=StubFailure.UNAVAILABLE)
    kit.gateway.complete(echo_request(f"note {secret}", correlation_id=f"corr2-{secret}"))
    assert len(kit.traces.records) == 2
    assert secret not in json.dumps(kit.traces.records)
    for record in kit.traces.records:
        assert list(VALIDATOR.iter_errors(record)) == []


def test_traces_hold_no_prompt_input_or_response_text(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, provider=FixedUsageProvider(content="distinct-reply-text"))
    kit.gateway.complete(echo_request("distinct-input-text"))
    dumped = json.dumps(kit.traces.records)
    assert "distinct-input-text" not in dumped
    assert "distinct-reply-text" not in dumped
    assert set(kit.traces.records[0]) <= set(SCHEMA["properties"])
