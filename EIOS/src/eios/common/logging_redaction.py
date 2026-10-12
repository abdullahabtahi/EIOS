"""Log redaction: secret-shaped strings never reach log output (FR-017).

Public API:
- ``REDACTED``: the replacement marker.
- ``redact_text(text) -> str``: replace secret shapes inside a string.
- ``redact_value(value) -> object``: rebuilt copy of a nested payload, input untouched.
- ``redact_exception(exc) -> str``: ``"TypeName: message"`` with secret shapes replaced.
- ``RedactingFilter``: ``logging.Filter``; add it to every handler that emits logs.

Redaction is pattern based (shapes mirror the repository secret scanner, plus bearer tokens,
JWTs and ``name=value`` assignments for common secret names) and key-name based (the whole value
under keys such as ``password`` or ``apiKey`` is hidden, so short or odd-looking secrets are
covered too). Attach the filter to handlers, not loggers, so records propagated from child
loggers are covered. It rewrites the LogRecord in place because logging offers no other hook;
that is the one deliberate mutation here. It never drops a record.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping

REDACTED = "[REDACTED]"

_MAX_DEPTH = 12
_KEY_VALUE_PATTERN = re.compile(
    r"([\w-]*?(?:password|passwd|secret|token|api[_-]?key|authorization))"
    r"([\"']?\s*[=:]\s*[\"']?)"
    r"(?!\[REDACTED\])[^\s\"',;]+",
    re.IGNORECASE,
)
# Whole-match shapes. Order matters: a full private-key block is consumed before its header.
_SHAPE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----.*?"
        r"-----END (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----",
        re.DOTALL,
    ),
    re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{22,255})\b"),
    re.compile(r"\bxox[abposr]-[0-9A-Za-z-]{10,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*"),
    re.compile(r"(?<=bearer )[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
)
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SENSITIVE_KEY = re.compile(
    r"(?:^|_)(?:password|passwd|secret|token|api_?key|authorization|credentials?|private_?key)$"
)
_STANDARD_RECORD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
}
_TRACEBACK_FORMATTER = logging.Formatter()


def redact_text(text: str) -> str:
    """Return ``text`` with secret-shaped substrings replaced by ``REDACTED``."""
    out = text
    for pattern in _SHAPE_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return _KEY_VALUE_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", out)


def redact_exception(exc: BaseException) -> str:
    """Render an exception as ``"TypeName: message"`` with secret shapes replaced."""
    return redact_text(f"{type(exc).__name__}: {exc}")


def redact_value(value: object) -> object:
    """Return a redacted copy of ``value``; containers are rebuilt, the input is not changed.

    Strings are scanned, mapping keys and values included. Values under secret-named keys are
    replaced whole. Other objects are rendered through ``repr`` and scanned. Nesting beyond a
    fixed depth is replaced by ``REDACTED`` (this also terminates self-referencing payloads).
    """
    return _walk(value, 0)


def _is_sensitive_key(key: str) -> bool:
    normalised = _CAMEL_BOUNDARY.sub("_", key).lower().replace("-", "_")
    return _SENSITIVE_KEY.search(normalised) is not None


def _walk_mapping(value: Mapping[object, object], depth: int) -> dict[object, object]:
    out: dict[object, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            out[key] = _walk(item, depth + 1)
        elif _is_sensitive_key(key):
            out[redact_text(key)] = REDACTED
        else:
            out[redact_text(key)] = _walk(item, depth + 1)
    return out


def _walk(value: object, depth: int) -> object:
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return redact_text(value)
    if depth >= _MAX_DEPTH:
        return REDACTED
    if isinstance(value, Mapping):
        return _walk_mapping(value, depth)
    if isinstance(value, list):
        return [_walk(item, depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(_walk(item, depth + 1) for item in value)
    if isinstance(value, set | frozenset):
        rebuilt = {_walk(item, depth + 1) for item in value}
        return frozenset(rebuilt) if isinstance(value, frozenset) else rebuilt
    if isinstance(value, BaseException):
        return redact_exception(value)
    return redact_text(repr(value))


def _redacted_message(record: logging.LogRecord) -> str:
    try:
        return redact_text(record.getMessage())
    except TypeError, ValueError:
        # Bad %-format arguments: never let logging raise into the caller, never emit raw args.
        return redact_text(str(record.msg)) + " [log arguments could not be formatted]"


class RedactingFilter(logging.Filter):
    """Redact message, arguments, extra attributes, traceback and stack info before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redacted_message(record)
        record.args = None
        if record.exc_info is not None and record.exc_info[0] is not None:
            record.exc_text = redact_text(_TRACEBACK_FORMATTER.formatException(record.exc_info))
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = redact_text(record.exc_text)
        if record.stack_info:
            record.stack_info = redact_text(record.stack_info)
        for name in set(vars(record)) - _STANDARD_RECORD_ATTRS:
            setattr(record, name, redact_value(getattr(record, name)))
        return True
