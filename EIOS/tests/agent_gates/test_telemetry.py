"""Telemetry events (US5): complete, pseudonymous, bounded, and scanned for raw identifiers (SC-008)."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from eios.agent_gates.records import TurnRecord
from eios.agent_gates.telemetry import redact_excerpt, scan_events, to_event

SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "specs"
        / "022-agent-quality-gates"
        / "contracts"
        / "telemetry-event.schema.json"
    ).read_text()
)
VALIDATOR = Draft202012Validator(SCHEMA)


def _record(question: str = "Check CR84920 for jane.doe@example.com") -> TurnRecord:
    return TurnRecord.model_validate(
        {
            "record_id": "c.0",
            "case_id": "c",
            "repeat": 0,
            "runtime": "copilot",
            "session_id": "sess-1",
            "turn_index": 1,
            "operator_id": "alice@deriv.example",
            "identity_source": "request_body",
            "role": "aml_investigator",
            "question": question,
            "tool_calls": [{"name": "inspect_aml_entity", "arguments": {}, "result": {"n": 1}}],
            "rounds": 1,
            "answer": "x",
            "is_replay_fallback": False,
            "data_origin": "fixture",
            "latency_ms": 5.0,
            "outcome": "completed",
        }
    )


def test_an_event_validates_and_carries_every_required_field() -> None:
    event = to_event(_record())
    assert not list(VALIDATOR.iter_errors(event)), list(VALIDATOR.iter_errors(event))
    assert event["tool_call_count"] == 1 and event["tool_names"] == ["inspect_aml_entity"]


def test_identifiers_become_tokens_and_text_is_redacted_and_bounded() -> None:
    event = to_event(_record("Check CR84920 for jane.doe@example.com " + "x" * 500))
    assert event["operator_token"].startswith("tok_") and "alice" not in json.dumps(event)
    excerpt = event["question_excerpt"]
    assert len(excerpt) <= 200 and "CR84920" not in excerpt and "jane.doe" not in excerpt


def test_the_scanner_finds_planted_raw_identifiers_and_passes_clean_events() -> None:
    clean = to_event(_record())
    assert scan_events([clean]) == []
    dirty: dict[str, Any] = clean | {"question_excerpt": "see CR84920 and bob@example.com"}
    assert len(scan_events([dirty])) >= 2


def test_redaction_masks_emails_and_identifier_shapes() -> None:
    assert redact_excerpt("mail bob@example.com about PTR-882") == "mail [email] about [id]"
