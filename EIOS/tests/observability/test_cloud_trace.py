"""Cloud Trace export for ADK's own spans, and the rule that no prompt or answer text rides on them."""

from __future__ import annotations

import logging
import os
from collections.abc import MutableMapping
from typing import Any

import pytest
from google.adk.telemetry.context import ContentCapturingMode
from google.adk.telemetry.setup import OTelHooks

from eios.common.errors import ConfigError
from eios.observability.cloud_trace import (
    ADK_SPAN_CONTENT_ENV,
    EXPORT_ENV,
    GENAI_CONTENT_ENV,
    TraceExport,
    configure_cloud_trace,
    run_telemetry,
)


class _Recorder:
    """Stands in for ADK's exporter factory and provider setup, recording what the app asked for."""

    def __init__(
        self, *, factory_error: Exception | None = None, no_processors: bool = False
    ) -> None:
        self.factory_calls: list[dict[str, bool]] = []
        self.setup_calls: list[list[Any]] = []
        self._factory_error = factory_error
        self._no_processors = no_processors

    def factory(self, **flags: bool) -> OTelHooks:
        self.factory_calls.append(flags)
        if self._factory_error is not None:
            raise self._factory_error
        return OTelHooks(span_processors=[] if self._no_processors else [object()])  # type: ignore[list-item]

    def setup(self, hooks: list[Any]) -> None:
        self.setup_calls.append(hooks)


def _configure(
    env: MutableMapping[str, str], rec: _Recorder, *, provider_installed: bool = False
) -> TraceExport:
    return configure_cloud_trace(
        env,
        exporters=rec.factory,
        set_providers=lambda hooks: rec.setup(hooks),
        provider_installed=lambda: provider_installed,
    )


def test_export_is_off_unless_asked_for() -> None:
    rec = _Recorder()
    assert _configure({}, rec) is TraceExport.OFF
    assert rec.factory_calls == [] and rec.setup_calls == []


def test_cloud_trace_asks_for_traces_only_not_metrics_or_logs() -> None:
    rec = _Recorder()
    assert _configure({EXPORT_ENV: "cloud_trace"}, rec) is TraceExport.CLOUD_TRACE
    assert rec.factory_calls == [
        {"enable_cloud_tracing": True, "enable_cloud_metrics": False, "enable_cloud_logging": False}
    ]
    assert len(rec.setup_calls) == 1
    assert rec.setup_calls[0][0].span_processors  # the exporter's processor goes first


def test_an_unknown_mode_fails_fast_instead_of_silently_exporting_nothing() -> None:
    with pytest.raises(ConfigError, match=EXPORT_ENV):
        _configure({EXPORT_ENV: "cloud-trace"}, _Recorder())


@pytest.mark.parametrize("prior", ["true", "1", "", "SPAN_AND_EVENT"])
def test_message_content_is_forced_off_whatever_the_environment_said(
    prior: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ADK_SPAN_CONTENT_ENV, prior)
    monkeypatch.setenv(GENAI_CONTENT_ENV, prior)
    monkeypatch.setenv(EXPORT_ENV, "cloud_trace")
    _configure(os.environ, _Recorder())
    assert os.environ[ADK_SPAN_CONTENT_ENV] == "false"
    assert os.environ[GENAI_CONTENT_ENV] == "NO_CONTENT"


def test_content_is_off_even_when_export_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """A later OTLP endpoint in the environment must not start shipping prompts."""
    monkeypatch.setenv(ADK_SPAN_CONTENT_ENV, "true")
    monkeypatch.delenv(EXPORT_ENV, raising=False)
    _configure(os.environ, _Recorder())
    assert os.environ[ADK_SPAN_CONTENT_ENV] == "false"


def test_a_failed_exporter_is_logged_and_never_stops_the_app(
    caplog: pytest.LogCaptureFixture,
) -> None:
    rec = _Recorder(factory_error=RuntimeError("no credentials"))
    with caplog.at_level(logging.ERROR):
        result = _configure({EXPORT_ENV: "cloud_trace"}, rec)
    assert result is TraceExport.FAILED
    assert rec.setup_calls == []
    assert any("Cloud Trace" in r.getMessage() for r in caplog.records)


def test_the_service_name_reaches_the_trace_resource() -> None:
    env = {EXPORT_ENV: "cloud_trace", "EIOS_SERVICE_NAME": "eios-api"}
    _configure(env, _Recorder())
    assert env["OTEL_SERVICE_NAME"] == "eios-api"


def test_an_explicit_otel_service_name_is_kept() -> None:
    env = {EXPORT_ENV: "cloud_trace", "OTEL_SERVICE_NAME": "custom"}
    _configure(env, _Recorder())
    assert env["OTEL_SERVICE_NAME"] == "custom"


def test_each_run_carries_a_no_content_telemetry_config() -> None:
    """Belt and braces: the per-run ADK config says no content too, so one env var cannot undo it."""
    config = run_telemetry()
    assert config.capture_message_content is ContentCapturingMode.NO_CONTENT
    assert not config.should_add_content_to_logs
    assert not config.should_add_content_to_legacy_spans


def test_run_telemetry_ignores_a_hostile_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADK_SPAN_CONTENT_ENV, "true")
    monkeypatch.setenv(GENAI_CONTENT_ENV, "SPAN_AND_EVENT")
    config = run_telemetry()
    assert not config.should_add_content_to_legacy_spans
    assert not config.should_add_content_to_logs


def test_no_exporter_from_adk_is_reported_as_failed_not_as_on(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ADK returns empty hooks when it cannot work out the project; saying "on" would send operators to an empty page."""
    rec = _Recorder(no_processors=True)
    with caplog.at_level(logging.ERROR):
        result = _configure({EXPORT_ENV: "cloud_trace"}, rec)
    assert result is TraceExport.FAILED
    assert rec.setup_calls == []
    assert any("no span exporter" in r.getMessage() for r in caplog.records)


def test_a_tracer_provider_installed_earlier_is_reported_not_silently_ignored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    rec = _Recorder()
    with caplog.at_level(logging.ERROR):
        result = _configure({EXPORT_ENV: "cloud_trace"}, rec, provider_installed=True)
    assert result is TraceExport.FAILED
    assert rec.setup_calls == []
    assert any("already" in r.getMessage() for r in caplog.records)
