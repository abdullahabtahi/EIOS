"""Turn Record contract tests (T005): the pydantic model and the published JSON schema must agree."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from eios.agent_gates.records import TurnRecord

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "022-agent-quality-gates"
    / "contracts"
    / "turn-record.schema.json"
)
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _good() -> dict[str, Any]:
    return {
        "record_id": "c1.0",
        "case_id": "c1",
        "repeat": 0,
        "runtime": "copilot",
        "session_id": "s1",
        "turn_index": 1,
        "operator_id": "tok_op_1",
        "identity_source": "request_body",
        "role": "aml_investigator",
        "question": "What is the discrepancy?",
        "tool_calls": [
            {
                "name": "inspect_aml_entity",
                "capability": "aml.dossier",
                "arguments": {"entity_id": "CR84920"},
                "result": {"discrepancy_multiplier": 16.0},
                "latency_ms": 3.0,
            }
        ],
        "rounds": 1,
        "answer": "It is 16.0x.",
        "is_replay_fallback": False,
        "data_origin": "fixture",
        "latency_ms": 12.0,
        "outcome": "completed",
    }


def _mutations() -> dict[str, dict[str, Any]]:
    replay = _good() | {"is_replay_fallback": True}
    inconclusive = _good() | {"outcome": "inconclusive"}
    both = _good()
    both["tool_calls"][0]["error"] = "NOT_FOUND"
    bad_role = _good() | {"role": "admin"}
    extra = _good() | {"surprise": 1}
    return {
        "replay_without_reason": replay,
        "inconclusive_without_reason": inconclusive,
        "result_and_error": both,
        "unknown_role": bad_role,
        "extra_field": extra,
    }


def test_a_valid_record_is_accepted_by_schema_and_model() -> None:
    data = _good()
    assert not list(VALIDATOR.iter_errors(data))
    record = TurnRecord.model_validate(data)
    assert record.record_id == "c1.0"


@pytest.mark.parametrize("name", list(_mutations()))
def test_invalid_records_are_rejected_by_both_schema_and_model(name: str) -> None:
    data = _mutations()[name]
    assert list(VALIDATOR.iter_errors(data)), f"schema accepted {name}"
    with pytest.raises(ValidationError):
        TurnRecord.model_validate(data)


def test_json_round_trip_is_lossless_and_schema_valid() -> None:
    record = TurnRecord.model_validate(_good())
    dumped = record.to_json_dict()
    assert not list(VALIDATOR.iter_errors(dumped))
    assert TurnRecord.model_validate(copy.deepcopy(dumped)) == record


def test_records_are_immutable() -> None:
    record = TurnRecord.model_validate(_good())
    with pytest.raises(ValidationError):
        record.answer = "changed"
