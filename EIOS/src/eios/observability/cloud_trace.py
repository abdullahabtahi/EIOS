"""Cloud Trace export for the spans ADK already emits, with prompt and answer text kept off them.

ADK wraps every turn in `invoke_agent`, `call_llm` and `execute_tool` spans. Without a tracer provider they go
nowhere, so a slow turn could only be explained from our own timing fields. `configure_cloud_trace` installs ADK's own
Google Cloud exporter (not a hand-written one) when `EIOS_TRACE_EXPORT=cloud_trace`, and stamps each span with the
request's correlation id so a trace and its log lines can be joined.

Some ADK spans carry the prompt and the model's answer by default, which here means account data. Content is switched
off on the paths the assistant runs: every run carries its own `TelemetryConfig` (the guarantee, whatever the
environment says), and the API's start-up also forces the process environment off (ADK reads it when a config is built),
even when export is off, so adding an OTLP endpoint later cannot start shipping text. A process that builds a runtime
without the API's start-up still has the per-run guarantee.

ADK exports over OTLP to telemetry.googleapis.com, so that API must be enabled in the project. Start-up reports
`FAILED`, loudly, when ADK produced no exporter (it does so when it cannot work out the project) or when a tracer
provider was installed first and would ignore ours; it never claims "on" for an export that is not happening.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, MutableMapping
from enum import Enum
from typing import Any

from google.adk.telemetry.context import ContentCapturingMode, TelemetryConfig
from google.adk.telemetry.google_cloud import get_gcp_exporters
from google.adk.telemetry.setup import OTelHooks, maybe_set_otel_providers
from opentelemetry import trace

from eios.common.errors import ConfigError
from eios.common.otel import correlation_span_processor

_LOG = logging.getLogger(__name__)

EXPORT_ENV = "EIOS_TRACE_EXPORT"
SERVICE_NAME_ENV = "EIOS_SERVICE_NAME"
ADK_SPAN_CONTENT_ENV = "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"
GENAI_CONTENT_ENV = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
_OTEL_SERVICE_NAME_ENV = "OTEL_SERVICE_NAME"
_MODES = {"": "off", "off": "off", "cloud_trace": "cloud_trace"}


class TraceExport(str, Enum):
    OFF = "off"
    CLOUD_TRACE = "cloud_trace"
    FAILED = "failed"  # asked for, could not be set up; the app serves without traces


def _force_content_off(environ: MutableMapping[str, str]) -> None:
    environ[ADK_SPAN_CONTENT_ENV] = "false"
    environ[GENAI_CONTENT_ENV] = ContentCapturingMode.NO_CONTENT.value


def run_telemetry() -> TelemetryConfig:
    """The per-run ADK telemetry config: no prompt or answer text on spans or log events, whatever the environment says."""
    return TelemetryConfig(capture_message_content=ContentCapturingMode.NO_CONTENT)


def _provider_installed() -> bool:
    return not isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider)


def configure_cloud_trace(
    environ: MutableMapping[str, str] | None = None,
    *,
    exporters: Callable[..., Any] = get_gcp_exporters,
    set_providers: Callable[[list[Any]], None] = maybe_set_otel_providers,
    provider_installed: Callable[[], bool] = _provider_installed,
) -> TraceExport:
    """Install the Cloud Trace exporter when asked; never raises for an export problem, always raises for a bad setting."""
    env = os.environ if environ is None else environ
    _force_content_off(env)
    raw = env.get(EXPORT_ENV, "").strip().lower()
    if raw not in _MODES:
        raise ConfigError(EXPORT_ENV, "mode", f"{raw!r} is not one of: off, cloud_trace")
    if _MODES[raw] == "off":
        return TraceExport.OFF
    service = env.get(SERVICE_NAME_ENV, "").strip()
    if service:
        env.setdefault(_OTEL_SERVICE_NAME_ENV, service)
    if provider_installed():
        _LOG.error("a tracer provider is already installed; Cloud Trace export was not added")
        return TraceExport.FAILED
    try:
        gcp = exporters(
            enable_cloud_tracing=True, enable_cloud_metrics=False, enable_cloud_logging=False
        )
        if not gcp.span_processors:
            _LOG.error(
                "ADK returned no span exporter for Cloud Trace (is the project set?); the service runs without traces"
            )
            return TraceExport.FAILED
        set_providers([gcp, OTelHooks(span_processors=[correlation_span_processor()])])
    except Exception:
        _LOG.exception("Cloud Trace export could not be set up; the service runs without traces")
        return TraceExport.FAILED
    _LOG.info("Cloud Trace export is on (no message content on spans)")
    return TraceExport.CLOUD_TRACE
