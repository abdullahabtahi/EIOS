"""The data plane is built while the service starts, so the first request never pays for it."""

import pytest
from fastapi.testclient import TestClient

from eios.api import app as app_module


def test_the_data_plane_is_built_during_start_up(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[bool] = []
    monkeypatch.setattr(app_module, "read_models", lambda: built.append(True))
    monkeypatch.setattr(app_module, "warm_up_assistant", lambda: _noop())
    with TestClient(app_module.create_app()):
        assert built == [True]


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
