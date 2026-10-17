"""Local-only OTLP trace export for development, and the rule that message text is captured only there."""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import Any

import pytest
from google.adk.telemetry.context import ContentCapturingMode
from google.adk.telemetry.setup import OTelHooks

from eios.common.errors import ConfigError
from eios.observability.cloud_trace import (
    ADK_SPAN_CONTENT_ENV,
    CAPTURE_CONTENT_ENV,
    EXPORT_ENV,
    GENAI_CONTENT_ENV,
    LOCAL_OTLP_ENDPOINT,
    TraceExport,
    configure_cloud_trace,
    run_telemetry,
)

_OTEL_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"


def _configure(
    env: MutableMapping[str, str], *, provider_installed: bool = False
) -> tuple[TraceExport, list[list[Any]]]:
    setups: list[list[Any]] = []
    result = configure_cloud_trace(
        env,
        exporters=lambda **_: pytest.fail(
            "the Google Cloud exporter must not be built for a local export"
        ),
        set_providers=setups.append,
        provider_installed=lambda: provider_installed,
    )
    return result, setups


@pytest.fixture(autouse=True)
def _reset_capture() -> Iterator[None]:
    """The capture switch is process state; leave it off for every other test."""
    yield
    configure_cloud_trace({}, set_providers=lambda _: None, provider_installed=lambda: False)


def _local(**extra: str) -> dict[str, str]:
    return {EXPORT_ENV: "otlp", "EIOS_ENVIRONMENT": "dev", **extra}


def test_otlp_mode_installs_a_correlation_hook_and_points_at_the_local_collector() -> None:
    env = _local()
    result, setups = _configure(env)
    assert result is TraceExport.OTLP_LOCAL
    assert env[_OTEL_ENDPOINT_ENV] == LOCAL_OTLP_ENDPOINT
    assert len(setups) == 1 and all(isinstance(h, OTelHooks) for h in setups[0])


def test_an_explicit_endpoint_is_kept() -> None:
    env = _local(**{_OTEL_ENDPOINT_ENV: "http://127.0.0.1:4318/v1/traces"})
    _configure(env)
    assert env[_OTEL_ENDPOINT_ENV] == "http://127.0.0.1:4318/v1/traces"


@pytest.mark.parametrize("environment", ["prod", "stage", "production", ""])
def test_otlp_export_is_refused_outside_dev_and_test(environment: str) -> None:
    env = {EXPORT_ENV: "otlp", "EIOS_ENVIRONMENT": environment}
    with pytest.raises(ConfigError):
        _configure(env)


def test_otlp_export_is_refused_when_the_environment_is_unset() -> None:
    with pytest.raises(ConfigError):
        _configure({EXPORT_ENV: "otlp"})


def test_content_stays_off_in_local_otlp_mode_unless_asked() -> None:
    env = _local()
    _configure(env)
    assert run_telemetry().capture_message_content is ContentCapturingMode.NO_CONTENT
    assert env[ADK_SPAN_CONTENT_ENV] == "false"
    assert env[GENAI_CONTENT_ENV] == ContentCapturingMode.NO_CONTENT.value


def test_content_is_captured_only_when_asked_in_local_otlp_mode() -> None:
    env = _local(**{CAPTURE_CONTENT_ENV: "1"})
    _configure(env)
    config = run_telemetry()
    assert config.capture_message_content is ContentCapturingMode.SPAN_ONLY
    assert config.should_add_content_to_legacy_spans
    assert not config.should_add_content_to_logs


def test_the_capture_flag_is_ignored_for_cloud_trace() -> None:
    env = {EXPORT_ENV: "cloud_trace", "EIOS_ENVIRONMENT": "dev", CAPTURE_CONTENT_ENV: "1"}
    configure_cloud_trace(
        env,
        exporters=lambda **_: OTelHooks(span_processors=[]),
        set_providers=lambda _: None,
        provider_installed=lambda: False,
    )
    assert run_telemetry().capture_message_content is ContentCapturingMode.NO_CONTENT
    assert env[ADK_SPAN_CONTENT_ENV] == "false"


def test_the_capture_flag_is_ignored_when_export_is_off() -> None:
    env = {"EIOS_ENVIRONMENT": "dev", CAPTURE_CONTENT_ENV: "1"}
    configure_cloud_trace(env)
    assert run_telemetry().capture_message_content is ContentCapturingMode.NO_CONTENT


def test_a_later_start_without_the_flag_turns_capture_back_off() -> None:
    _configure(_local(**{CAPTURE_CONTENT_ENV: "1"}))
    _configure(_local())
    assert run_telemetry().capture_message_content is ContentCapturingMode.NO_CONTENT


def test_a_tracer_provider_installed_earlier_is_reported_as_failed() -> None:
    result, setups = _configure(_local(), provider_installed=True)
    assert result is TraceExport.FAILED
    assert setups == []
