"""T063 (FR-017): secret-shaped strings never reach log output."""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator

import pytest

from eios.common.logging_redaction import (
    REDACTED,
    RedactingFilter,
    redact_exception,
    redact_text,
    redact_value,
)
from tests.support.secret_shapes import all_shapes, api_key, vcs_token

_SHAPES = all_shapes()


def _jwt() -> str:
    return ".".join(
        ["eyJ" + "hbGciOiJIUzI1NiJ9", "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0", "c2lnbmF0dXJl"]
    )


@pytest.mark.parametrize("name", sorted(_SHAPES))
def test_each_secret_shape_is_redacted_in_text(name: str) -> None:
    secret = _SHAPES[name]
    out = redact_text(f"before {secret} after")
    assert secret not in out
    assert REDACTED in out
    assert out.startswith("before ")
    assert out.endswith(" after")


def test_private_key_body_is_redacted_not_just_the_header() -> None:
    block = _SHAPES["private_key_block"]
    body_line = block.splitlines()[1]
    assert body_line not in redact_text(f"key: {block}")


def test_bearer_tokens_jwts_and_assignments_are_redacted() -> None:
    jwt = _jwt()
    bearer = "Bearer " + "q" * 24
    out = redact_text(f"Authorization: {bearer} jwt={jwt} password=hunter2hunter2")
    assert jwt not in out
    assert "q" * 24 not in out
    assert "hunter2hunter2" not in out


def test_clean_text_is_returned_unchanged() -> None:
    text = "order 42 shipped; max_tokens=256 and token_count=3"
    assert redact_text(text) == text


def test_exception_text_is_redacted() -> None:
    secret = api_key()
    out = redact_exception(ValueError(f"upstream rejected key {secret}"))
    assert secret not in out
    assert out.startswith("ValueError: ")


def test_nested_payload_is_redacted_without_mutating_the_input() -> None:
    secret = vcs_token()
    payload = {
        "event": "call",
        "detail": {"note": f"saw {secret}", "items": [f"x {secret}", 3, ("a", secret)]},
        "count": 7,
        "ok": True,
        "nothing": None,
    }
    out = redact_value(payload)
    assert secret not in repr(out)
    assert out == {
        "event": "call",
        "detail": {
            "note": f"saw {REDACTED}",
            "items": [f"x {REDACTED}", 3, ("a", REDACTED)],
        },
        "count": 7,
        "ok": True,
        "nothing": None,
    }
    assert secret in repr(payload)  # the caller's object is untouched
    assert out is not payload


def test_secret_in_a_mapping_key_is_redacted() -> None:
    secret = api_key()
    out = redact_value({secret: "v"})
    assert secret not in repr(out)


def test_sensitive_key_names_hide_the_whole_value() -> None:
    out = redact_value(
        {
            "password": "short",
            "apiKey": {"nested": "value"},
            "service_token": "t",
            "Authorization": "x",
            "max_tokens": 256,
            "token_count": 5,
        }
    )
    assert out == {
        "password": REDACTED,
        "apiKey": REDACTED,
        "service_token": REDACTED,
        "Authorization": REDACTED,
        "max_tokens": 256,
        "token_count": 5,
    }


def test_sets_and_frozensets_are_redacted() -> None:
    secret = api_key()
    out = redact_value({"s": {secret, "ok"}, "f": frozenset({secret})})
    assert secret not in repr(out)


def test_unknown_objects_are_rendered_redacted() -> None:
    class Holder:
        def __repr__(self) -> str:
            return f"Holder({vcs_token()})"

    out = redact_value({"h": Holder()})
    assert vcs_token() not in repr(out)


def test_self_referencing_payload_terminates() -> None:
    looped: list[object] = []
    looped.append(looped)
    assert redact_value(looped) is not None


@pytest.fixture
def captured() -> Iterator[tuple[logging.Logger, io.StringIO]]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(message)s | %(payload)s"))
    logger = logging.getLogger("test.redaction.logger")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    yield logger, stream
    logger.handlers = []


def test_filter_redacts_message_args_extra_and_traceback(
    captured: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, stream = captured
    secret = api_key()
    token = vcs_token()
    try:
        raise RuntimeError(f"boom {secret}")
    except RuntimeError:
        logger.error(
            "failed with %s",
            token,
            extra={"payload": {"password": "p", "note": f"n {secret}"}},
            exc_info=True,
        )
    output = stream.getvalue()
    assert secret not in output
    assert token not in output
    assert '"p"' not in output
    assert "RuntimeError" in output
    assert REDACTED in output


def test_filter_never_drops_records() -> None:
    record = logging.LogRecord("n", logging.INFO, __file__, 1, "plain %s", ("x",), None)
    assert RedactingFilter().filter(record) is True
    assert record.getMessage() == "plain x"


def test_non_string_keys_and_exceptions_inside_payloads() -> None:
    secret = api_key()
    out = redact_value({1: "a", "err": ValueError(f"bad {secret}")})
    assert secret not in repr(out)
    assert isinstance(out, dict)
    assert out[1] == "a"


def test_filter_survives_bad_format_arguments_and_redacts_stack_and_cached_traceback() -> None:
    secret = vcs_token()
    record = logging.LogRecord("n", logging.ERROR, __file__, 1, "needs %d", ("x",), None)
    record.stack_info = f"stack {secret}"
    record.exc_text = f"cached {secret}"
    assert RedactingFilter().filter(record) is True
    assert "needs" in record.getMessage()
    assert secret not in (record.stack_info or "")
    assert secret not in (record.exc_text or "")


def test_filter_redacts_a_secret_hidden_in_a_bad_format_message() -> None:
    secret = vcs_token()
    record = logging.LogRecord("n", logging.ERROR, __file__, 1, f"{secret} %d", ("x",), None)
    RedactingFilter().filter(record)
    assert secret not in record.getMessage()
