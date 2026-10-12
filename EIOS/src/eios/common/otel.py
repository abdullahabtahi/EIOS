# ruff: noqa: E501
"""Telemetry setup (FR-036): tracer, structured JSON logs and trace-context propagation.

This is the only module allowed to import the telemetry SDK (ruff ``TID251`` ignores this file
only); every other module uses ``opentelemetry.trace`` or the helpers here.

Public API:
- ``setup_telemetry(service_name, ...) -> Telemetry``: one tracer provider per call (no global
  state, so tests and in-process services stay isolated) and one JSON log handler on the logger
  ``eios.service.<service_name>``; calling it again replaces the handler, never adds a second.
- Every span gets a ``correlation_id`` attribute at start; every log record carries
  ``correlation_id``, ``service`` and, inside a span, ``trace_id`` / ``span_id``. Log records pass
  through ``RedactingFilter`` before they are written.
- Exporter selection: an injected exporter wins; else ``EIOS_OTEL_EXPORTER_ENDPOINT`` selects the
  OTLP exporter; with neither, a no-op exporter is installed (never raises).
- ``inject_trace_headers`` / ``extract_trace_context``: W3C ``traceparent`` propagation so spans
  from two services share one trace.
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import ModuleType
from typing import IO

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from eios.common.correlation import current_id
from eios.common.errors import ConfigError
from eios.common.logging_redaction import RedactingFilter

ENV_SERVICE_NAME = "EIOS_SERVICE_NAME"
ENV_EXPORTER_ENDPOINT = "EIOS_OTEL_EXPORTER_ENDPOINT"

MemorySpanExporter = InMemorySpanExporter

# [SPIKE] The OTLP exporter package is not a dependency yet; choosing and locking it is open.
_OTLP_EXPORTER_MODULE = "opentelemetry.exporter.otlp.proto.http.trace_exporter"
_SERVICE_NAME = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_NO_ID = "-"
_HANDLER_MARK = "_eios_telemetry_handler"
_PROPAGATOR = TraceContextTextMapPropagator()
_import_module: Callable[[str], ModuleType] = importlib.import_module
_RESERVED = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "correlation_id",
    "service",
    "trace_id",
    "span_id",
}


@dataclass(frozen=True)
class Telemetry:
    """Handles returned by ``setup_telemetry``."""

    service_name: str
    tracer: trace.Tracer
    logger: logging.Logger
    exporter_kind: str
    shutdown: Callable[[], None]


class _NoopExporter(SpanExporter):
    """Accepts and drops spans; used when no exporter endpoint is configured."""

    def export(self, spans: Sequence[object]) -> SpanExportResult:
        return SpanExportResult.SUCCESS


class _CorrelationSpanProcessor(SpanProcessor):
    """Stamps the current correlation id on every span at start."""

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        span.set_attribute("correlation_id", current_id() or _NO_ID)


class _ContextFilter(logging.Filter):
    """Adds correlation id, service and active trace ids to each record."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = current_id() or _NO_ID
        record.service = self._service
        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            record.trace_id = format(context.trace_id, "032x")
            record.span_id = format(context.span_id, "016x")
        return True


class _JsonFormatter(logging.Formatter):
    """One JSON object per line; newlines in text are escaped, so a record cannot be forged."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", ""),
            "correlation_id": getattr(record, "correlation_id", _NO_ID),
            "message": record.getMessage(),
        }
        for key in ("trace_id", "span_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_text:
            payload["exception"] = record.exc_text
        extras = {k: v for k, v in vars(record).items() if k not in _RESERVED}
        if extras:
            payload["extra"] = extras
        return json.dumps(payload, default=str)


def new_memory_exporter() -> MemorySpanExporter:
    """An in-memory span exporter for tests."""
    return MemorySpanExporter()


def _validated_name(name: str, source: str) -> str:
    if not _SERVICE_NAME.fullmatch(name):
        raise ConfigError(source, "service_name", "must be 1-64 letters, digits, '_', '.' or '-'")
    return name


def service_name_from_env(environ: Mapping[str, str] | None = None, *, default: str) -> str:
    """Service name from ``EIOS_SERVICE_NAME`` (``default`` when unset), validated."""
    env = os.environ if environ is None else environ
    return _validated_name(env.get(ENV_SERVICE_NAME, default), ENV_SERVICE_NAME)


def _otlp_exporter(endpoint: str) -> SpanExporter:
    try:
        exporter: SpanExporter = _import_module(_OTLP_EXPORTER_MODULE).OTLPSpanExporter(
            endpoint=endpoint
        )
    except (ImportError, AttributeError) as exc:
        raise ConfigError(
            ENV_EXPORTER_ENDPOINT,
            "exporter",
            "an endpoint is set but no OTLP exporter is installed",
        ) from exc
    return exporter


def _select_exporter(
    injected: SpanExporter | None, environ: Mapping[str, str]
) -> tuple[SpanExporter, str]:
    if injected is not None:
        return injected, "injected"
    endpoint = environ.get(ENV_EXPORTER_ENDPOINT, "").strip()
    if endpoint:
        return _otlp_exporter(endpoint), "otlp"
    return _NoopExporter(), "noop"


def _install_log_handler(service_name: str, stream: IO[str]) -> logging.Logger:
    logger = logging.getLogger(f"eios.service.{service_name}")
    for old in [h for h in logger.handlers if getattr(h, _HANDLER_MARK, False)]:
        logger.removeHandler(old)
    handler = logging.StreamHandler(stream)
    setattr(handler, _HANDLER_MARK, True)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_ContextFilter(service_name))
    handler.addFilter(RedactingFilter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def setup_telemetry(
    service_name: str,
    *,
    environ: Mapping[str, str] | None = None,
    span_exporter: SpanExporter | None = None,
    log_stream: IO[str] | None = None,
) -> Telemetry:
    """Wire a tracer and JSON logger for ``service_name``; safe to call repeatedly."""
    env = os.environ if environ is None else environ
    name = _validated_name(service_name, "setup_telemetry")
    exporter, kind = _select_exporter(span_exporter, env)
    provider = TracerProvider(resource=Resource.create({"service.name": name}))
    provider.add_span_processor(_CorrelationSpanProcessor())
    provider.add_span_processor(
        BatchSpanProcessor(exporter) if kind == "otlp" else SimpleSpanProcessor(exporter)
    )
    logger = _install_log_handler(name, log_stream if log_stream is not None else sys.stderr)
    return Telemetry(name, provider.get_tracer(name), logger, kind, provider.shutdown)


def inject_trace_headers(headers: Mapping[str, str] | None = None) -> dict[str, str]:
    """Copy of ``headers`` plus the W3C ``traceparent`` of the current span."""
    carrier = dict(headers or {})
    _PROPAGATOR.inject(carrier)
    return carrier


def extract_trace_context(headers: Mapping[str, str]) -> Context:
    """Trace context from inbound headers; empty (new root) if absent or malformed."""
    carrier = {key.lower(): value for key, value in headers.items()}
    return _PROPAGATOR.extract(carrier, context=Context())
