"""The data plane is built while the service starts, so the first request never pays for it."""

import pytest
from fastapi.testclient import TestClient

from eios.api import app as app_module
from eios.observability.cloud_trace import TraceExport


@pytest.fixture(autouse=True)
def _no_real_trace_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start-up configures tracing; a test must not install a process-wide tracer provider or change os.environ."""
    monkeypatch.setattr(app_module, "configure_cloud_trace", lambda: TraceExport.OFF)


def test_the_data_plane_is_built_during_start_up(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[bool] = []
    monkeypatch.setattr(app_module, "read_models", lambda: built.append(True))
    monkeypatch.setattr(app_module, "warm_up_assistant", lambda: _noop())
    with TestClient(app_module.create_app()):
        assert built == [True]


def test_tracing_is_configured_before_the_first_turn_can_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    monkeypatch.setattr(app_module, "configure_cloud_trace", lambda: order.append("trace"))
    monkeypatch.setattr(app_module, "read_models", lambda: order.append("plane"))
    monkeypatch.setattr(app_module, "warm_up_assistant", lambda: _noop())
    with TestClient(app_module.create_app()):
        assert order == ["trace", "plane"]


def test_a_failed_build_does_not_stop_the_service_from_starting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> None:
        raise RuntimeError("engine fault")

    monkeypatch.setattr(app_module, "read_models", broken)
    monkeypatch.setattr(app_module, "warm_up_assistant", lambda: _noop())
    with TestClient(app_module.create_app()) as client:
        assert (
            client.get("/health").status_code == 200
        )  # up, and the next request retries the build


async def _noop() -> None:
    return None
