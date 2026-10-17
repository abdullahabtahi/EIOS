"""Per-turn telemetry events (spec 022, US5): pseudonymous tokens, redacted bounded text, a scanner.

Names follow the OpenTelemetry GenAI conventions where one exists (see the schema's `x-otel` notes). The
writer in production is the ADK analytics plugin (spec 021); this module defines what an event may contain,
and proves no raw identifier gets into one.
"""

import hashlib
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from eios.agent_gates.records import TurnRecord

EXCERPT_LIMIT = 200
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_IDENT = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]*?\d{2,}[A-Za-z0-9_-]*\b")
_SCANNED_TEXT_FIELDS = (
    "question_excerpt",
    "fallback_reason",
    "audit_verdict",
    "runtime",
    "case_id",
)


def token(value: str) -> str:
    return "tok_" + hashlib.sha256(value.encode()).hexdigest()[:12]


def redact_excerpt(text: str, limit: int = EXCERPT_LIMIT) -> str:
    return _IDENT.sub("[id]", _EMAIL.sub("[email]", text))[:limit]


def to_event(record: TurnRecord) -> dict[str, Any]:
    return {
        "event_id": hashlib.sha256(record.record_id.encode()).hexdigest()[:16],
        "ts": datetime.now(UTC).isoformat(),
        "operator_token": token(record.operator_id),
        "session_token": token(record.session_id),
        "runtime": record.runtime,
        "role": record.role.value,
        "tool_call_count": len(record.tool_calls),
        "tool_names": [c.name for c in record.tool_calls],
        "rounds": record.rounds,
        "latency_ms": record.latency_ms,
        "tokens_in": record.tokens_in,
        "tokens_out": record.tokens_out,
        "cost_usd": record.cost_usd,
        "is_replay_fallback": record.is_replay_fallback,
        "fallback_reason": record.fallback_reason,
        "audit_verdict": record.audit_verdict,
        "citation_count": len(record.citations),
        "data_origin": record.data_origin.value,
        "question_excerpt": redact_excerpt(record.question),
        "case_id": record.case_id,
    }


def scan_events(events: Sequence[Mapping[str, Any]]) -> list[str]:
    """Raw identifiers (emails, identifier-shaped tokens) found in an event's free-text fields."""
    findings: list[str] = []
    for event in events:
        values: list[str] = []
        for key in _SCANNED_TEXT_FIELDS:
            if isinstance(event.get(key), str):
                values.append(event[key])
        values += [str(n) for n in event.get("tool_names", [])]
        for value in values:
            findings += _EMAIL.findall(value)
            findings += [m for m in _IDENT.findall(value) if not m.startswith("tok_")]
    return findings
