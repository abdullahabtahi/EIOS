"""T186 (constitution II, plan gate G2): skeletons expose health and one GET correlation route."""

from __future__ import annotations

import io
from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI

from eios.common.otel import Telemetry, new_memory_exporter, setup_telemetry
from services.skeleton_core.app import create_app as create_core
from services.skeleton_edge.app import create_app as create_edge

_ALLOWED_BODY_KEYS = {"status", "correlation_id", "core_correlation_id", "error"}
_FORBIDDEN_METHODS = ("post", "put", "patch", "delete")


def _telemetry(name: str) -> Telemetry:
    return setup_telemetry(name, span_exporter=new_memory_exporter(), log_stream=io.StringIO())


class _ExplodingTransport(httpx.AsyncBaseTransport):
    """Fails the test if the edge touches core while serving a request that must not."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"unexpected outbound call: {request.url.path}")


def _core() -> FastAPI:
    return create_core(telemetry=_telemetry("skeleton_core"))


def _edge() -> FastAPI:
    client = httpx.AsyncClient(transport=_ExplodingTransport(), base_url="http://core.invalid")
    return create_edge(telemetry=_telemetry("skeleton_edge"), core_client=client)


_CASES: dict[str, tuple[Callable[[], FastAPI], set[str]]] = {
    "skeleton_core": (_core, {"/health", "/echo"}),
    "skeleton_edge": (_edge, {"/health", "/forward"}),
}


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://svc.invalid")


@pytest.mark.parametrize("name", sorted(_CASES))
def test_openapi_lists_exactly_the_health_and_correlation_routes_with_get_only(name: str) -> None:
    factory, expected = _CASES[name]
    paths = factory().openapi()["paths"]
    assert set(paths) == expected
    for path, operations in paths.items():
        assert set(operations) == {"get"}, path


@pytest.mark.parametrize("name", sorted(_CASES))
@pytest.mark.anyio
async def test_mutating_methods_answer_405(name: str) -> None:
    factory, expected = _CASES[name]
    async with _client(factory()) as client:
        for path in sorted(expected):
            for method in _FORBIDDEN_METHODS:
                response = await client.request(method.upper(), path)
                assert response.status_code == 405, (path, method)


@pytest.mark.parametrize("name", sorted(_CASES))
@pytest.mark.anyio
async def test_unknown_paths_are_404_and_docs_are_not_served(name: str) -> None:
    factory, _ = _CASES[name]
    async with _client(factory()) as client:
        for path in ("/metrics", "/docs", "/redoc", "/openapi.json", "/admin"):
            assert (await client.get(path)).status_code == 404, path


@pytest.mark.parametrize("name", sorted(_CASES))
@pytest.mark.anyio
async def test_health_answers_without_touching_other_services(name: str) -> None:
    factory, _ = _CASES[name]
    async with _client(factory()) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_no_route_returns_a_business_metric() -> None:
    async with _client(_core()) as client:
        for path in ("/health", "/echo"):
            body = (await client.get(path)).json()
            assert set(body) <= _ALLOWED_BODY_KEYS, path
            assert all(isinstance(v, str) for v in body.values()), path
