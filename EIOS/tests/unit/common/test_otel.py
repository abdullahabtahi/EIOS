# ruff: noqa: E501
"""T185 (FR-036, FR-017): spans and logs carry the correlation id; redaction; env-driven setup."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from eios.common import otel
from eios.common.correlation import correlation_scope
from eios.common.errors import ConfigError
from eios.common.logging_redaction import REDACTED
from eios.common.otel import (
    ENV_EXPORTER_ENDPOINT,
    ENV_SERVICE_NAME,
    MemorySpanExporter,
    extract_trace_context,
    inject_trace_headers,
    new_memory_exporter,
    service_name_from_env,
    setup_telemetry,
)
from tests.support.secret_shapes import api_key, vcs_token

REPO_ROOT = Path(__file__).resolve().parents[3]


def _records(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_every_span_carries_the_correlation_id() -> None:
    exporter = new_memory_exporter()
    telemetry = setup_telemetry("svc-span", span_exporter=exporter, log_stream=io.StringIO())
    with correlation_scope("cid-span-1"):
        with telemetry.tracer.start_as_current_span("outer"):
            with telemetry.tracer.start_as_current_span("inner"):
                pass
    spans = exporter.get_finished_spans()
    assert {s.name for s in spans} == {"outer", "inner"}
    for span in spans:
        assert span.attributes is not None
        assert span.attributes["correlation_id"] == "cid-span-1"
        assert span.resource.attributes["service.name"] == "svc-span"
    telemetry.shutdown()


def test_every_log_record_carries_the_correlation_id_and_service() -> None:
    stream = io.StringIO()
    telemetry = setup_telemetry("svc-log", span_exporter=new_memory_exporter(), log_stream=stream)
    with correlation_scope("cid-log-1"):
        telemetry.logger.info("first")
        telemetry.logger.warning("second")
    telemetry.logger.info("outside any scope")
    records = _records(stream)
    assert [r["message"] for r in records] == ["first", "second", "outside any scope"]
    assert [r["correlation_id"] for r in records[:2]] == ["cid-log-1", "cid-log-1"]
    assert records[2]["correlation_id"] == "-"
    assert all(r["service"] == "svc-log" for r in records)
    assert {r["level"] for r in records[:2]} == {"INFO", "WARNING"}
    telemetry.shutdown()


def test_log_records_inside_a_span_carry_trace_and_span_ids() -> None:
    stream = io.StringIO()
    exporter = new_memory_exporter()
    telemetry = setup_telemetry("svc-trace-log", span_exporter=exporter, log_stream=stream)
    with correlation_scope("cid-tl"), telemetry.tracer.start_as_current_span("work"):
        telemetry.logger.info("inside")
    (record,) = _records(stream)
    (span,) = exporter.get_finished_spans()
    assert span.context is not None
    assert record["trace_id"] == format(span.context.trace_id, "032x")
    assert record["span_id"] == format(span.context.span_id, "016x")
    telemetry.shutdown()


@pytest.mark.parametrize("secret", [api_key(), vcs_token()])
def test_log_messages_pass_through_redaction(secret: str) -> None:
    stream = io.StringIO()
    telemetry = setup_telemetry(
        "svc-redact", span_exporter=new_memory_exporter(), log_stream=stream
    )
    with correlation_scope("cid-redact"):
        telemetry.logger.info("calling with %s", secret, extra={"detail": f"key {secret}"})
        telemetry.logger.error("failed", exc_info=RuntimeError(f"boom {secret}"))
    raw = stream.getvalue()
    assert secret not in raw
    assert REDACTED in raw
    telemetry.shutdown()


def test_hostile_message_text_cannot_forge_a_log_line() -> None:
    stream = io.StringIO()
    telemetry = setup_telemetry(
        "svc-inject", span_exporter=new_memory_exporter(), log_stream=stream
    )
    with correlation_scope("cid-inject"):
        telemetry.logger.info("line one\nline two")
    assert len(stream.getvalue().splitlines()) == 1
    telemetry.shutdown()


def test_service_name_comes_from_the_environment_with_a_default() -> None:
    assert service_name_from_env({ENV_SERVICE_NAME: "from-env"}, default="fallback") == "from-env"
    assert service_name_from_env({}, default="fallback") == "fallback"


@pytest.mark.parametrize("bad", ["", "   ", "has space", "x" * 200, "new\nline"])
def test_invalid_service_name_is_a_config_error(bad: str) -> None:
    with pytest.raises(ConfigError, match=ENV_SERVICE_NAME):
        service_name_from_env({ENV_SERVICE_NAME: bad}, default="fallback")


def test_no_endpoint_installs_a_noop_exporter_and_does_not_raise() -> None:
    telemetry = setup_telemetry("svc-noop", environ={}, log_stream=io.StringIO())
    assert telemetry.exporter_kind == "noop"
    with correlation_scope("cid-noop"), telemetry.tracer.start_as_current_span("x"):
        telemetry.logger.info("fine")
    telemetry.shutdown()


def test_endpoint_comes_from_the_environment_and_selects_the_otlp_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    class FakeExporter(MemorySpanExporter):
        def __init__(self, endpoint: str) -> None:
            super().__init__()
            seen["endpoint"] = endpoint

    monkeypatch.setattr(
        otel, "_import_module", lambda name: SimpleNamespace(OTLPSpanExporter=FakeExporter)
    )
    configured = "configured-endpoint-value"
    telemetry = setup_telemetry(
        "svc-otlp", environ={ENV_EXPORTER_ENDPOINT: configured}, log_stream=io.StringIO()
    )
    assert telemetry.exporter_kind == "otlp"
    assert seen == {"endpoint": configured}
    telemetry.shutdown()


def test_endpoint_without_the_exporter_package_is_an_explicit_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(name: str) -> object:
        raise ImportError(name)

    monkeypatch.setattr(otel, "_import_module", missing)
    with pytest.raises(ConfigError, match=ENV_EXPORTER_ENDPOINT):
        setup_telemetry("svc-missing", environ={ENV_EXPORTER_ENDPOINT: "x"})


def test_blank_endpoint_is_treated_as_unset() -> None:
    telemetry = setup_telemetry(
        "svc-blank", environ={ENV_EXPORTER_ENDPOINT: "  "}, log_stream=io.StringIO()
    )
    assert telemetry.exporter_kind == "noop"
    telemetry.shutdown()


def test_setup_twice_does_not_duplicate_handlers() -> None:
    first = io.StringIO()
    second = io.StringIO()
    one = setup_telemetry("svc-twice", span_exporter=new_memory_exporter(), log_stream=first)
    two = setup_telemetry("svc-twice", span_exporter=new_memory_exporter(), log_stream=second)
    assert one.logger is two.logger
    assert len(two.logger.handlers) == 1
    two.logger.info("once")
    assert first.getvalue() == ""
    assert len(second.getvalue().splitlines()) == 1
    one.shutdown()
    two.shutdown()


def test_trace_context_round_trips_through_headers() -> None:
    exporter = new_memory_exporter()
    telemetry = setup_telemetry("svc-prop", span_exporter=exporter, log_stream=io.StringIO())
    with telemetry.tracer.start_as_current_span("parent"):
        headers = inject_trace_headers({"Accept": "x"})
    assert headers["Accept"] == "x"
    assert re.fullmatch(r"00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}", headers["traceparent"])
    with telemetry.tracer.start_as_current_span("child", context=extract_trace_context(headers)):
        pass
    parent, child = exporter.get_finished_spans()
    assert parent.context is not None and child.context is not None
    assert child.context.trace_id == parent.context.trace_id
    assert child.parent is not None
    assert child.parent.span_id == parent.context.span_id
    telemetry.shutdown()


def test_extract_ignores_a_malformed_traceparent() -> None:
    exporter = new_memory_exporter()
    telemetry = setup_telemetry("svc-bad-tp", span_exporter=exporter, log_stream=io.StringIO())
    context = extract_trace_context({"traceparent": "not-a-valid-value\n"})
    with telemetry.tracer.start_as_current_span("root", context=context):
        pass
    (span,) = exporter.get_finished_spans()
    assert span.parent is None
    telemetry.shutdown()


def test_no_endpoint_or_address_literal_exists_in_code() -> None:
    pattern = re.compile(r"https?://|localhost|\b\d{1,3}(?:\.\d{1,3}){3}\b|:\d{4,5}\b")
    files = [
        REPO_ROOT / "src/eios/common/otel.py",
        REPO_ROOT / "src/eios/common/correlation.py",
        REPO_ROOT / "src/eios/common/http_correlation.py",
        REPO_ROOT / "services/skeleton_core/app.py",
        REPO_ROOT / "services/skeleton_edge/app.py",
    ]
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            assert not pattern.search(line), f"{path.name}:{number}: {line.strip()}"
