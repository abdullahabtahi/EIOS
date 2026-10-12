"""T187 (SC-010, US6 scenario 1): one correlation id and one trace across edge and core."""

from __future__ import annotations

import io
import json
from dataclasses import dataclass

import httpx
import pytest
from fastapi import FastAPI

from eios.common.correlation import CORRELATION_HEADER, MAX_ID_LENGTH, is_valid_correlation_id
from eios.common.otel import Telemetry, new_memory_exporter, setup_telemetry
from services.skeleton_core.app import create_app as create_core
from services.skeleton_edge.app import create_app as create_edge


@dataclass
class Rig:
    exporter: object
    edge_app: FastAPI
    core_app: FastAPI
    edge_log: io.StringIO
    core_log: io.StringIO
    edge_telemetry: Telemetry
    core_telemetry: Telemetry

    def spans(self, service: str) -> list[object]:
        return [
            s
            for s in self.exporter.get_finished_spans()  # type: ignore[attr-defined]
            if s.resource.attributes["service.name"] == service
        ]


def _build(core_transport: httpx.AsyncBaseTransport | None = None) -> Rig:
    exporter = new_memory_exporter()
    core_log, edge_log = io.StringIO(), io.StringIO()
    core_t = setup_telemetry("skeleton_core", span_exporter=exporter, log_stream=core_log)
    edge_t = setup_telemetry("skeleton_edge", span_exporter=exporter, log_stream=edge_log)
    core_app = create_core(telemetry=core_t)
    transport = core_transport or httpx.ASGITransport(app=core_app)
    core_client = httpx.AsyncClient(transport=transport, base_url="http://core.invalid")
    edge_app = create_edge(telemetry=edge_t, core_client=core_client)
    return Rig(exporter, edge_app, core_app, edge_log, core_log, edge_t, core_t)


async def _call(rig: Rig, headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=rig.edge_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://edge.invalid") as client:
        return await client.get("/forward", headers=headers or {})


def _log_ids(stream: io.StringIO) -> set[str]:
    return {json.loads(line)["correlation_id"] for line in stream.getvalue().splitlines()}


def _span_ids(rig: Rig, service: str) -> set[str]:
    spans = rig.spans(service)
    assert spans, f"no spans from {service}"
    return {s.attributes["correlation_id"] for s in spans}  # type: ignore[attr-defined]


def _assert_everywhere(rig: Rig, response: httpx.Response, expected: str | None) -> str:
    header = response.headers[CORRELATION_HEADER]
    assert is_valid_correlation_id(header)
    if expected is not None:
        assert header == expected
    assert _span_ids(rig, "skeleton_edge") == {header}
    assert _span_ids(rig, "skeleton_core") == {header}
    assert _log_ids(rig.edge_log) == {header}
    assert _log_ids(rig.core_log) == {header}
    return header


def _one_trace(rig: Rig) -> None:
    spans = rig.exporter.get_finished_spans()  # type: ignore[attr-defined]
    assert {s.context.trace_id for s in spans} and len({s.context.trace_id for s in spans}) == 1
    assert rig.spans("skeleton_edge") and rig.spans("skeleton_core")


@pytest.mark.anyio
async def test_a_new_id_is_generated_and_appears_in_all_four_places() -> None:
    rig = _build()
    response = await _call(rig)
    assert response.status_code == 200
    header = _assert_everywhere(rig, response, None)
    body = response.json()
    assert body == {"correlation_id": header, "core_correlation_id": header}
    _one_trace(rig)


@pytest.mark.anyio
async def test_a_valid_supplied_id_is_preserved_in_all_four_places() -> None:
    rig = _build()
    response = await _call(rig, {CORRELATION_HEADER: "client-supplied-42"})
    assert response.status_code == 200
    _assert_everywhere(rig, response, "client-supplied-42")
    _one_trace(rig)


@pytest.mark.anyio
@pytest.mark.parametrize("bad", ["has space", "x" * (MAX_ID_LENGTH + 1), "inject%0Ad", "a_b"])
async def test_an_invalid_id_is_replaced_identically_in_both_services(bad: str) -> None:
    rig = _build()
    response = await _call(rig, {CORRELATION_HEADER: bad})
    assert response.status_code == 200
    header = _assert_everywhere(rig, response, None)
    assert header != bad
    assert bad not in rig.edge_log.getvalue() + rig.core_log.getvalue()
    assert response.json()["core_correlation_id"] == header


class _FailingCore(httpx.AsyncBaseTransport):
    def __init__(self, response: httpx.Response | None) -> None:
        self._response = response

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self._response is None:
            raise httpx.ConnectError("core unreachable", request=request)
        return self._response


@pytest.mark.anyio
@pytest.mark.parametrize(
    "core_response",
    [None, httpx.Response(500, json={"x": "y"}), httpx.Response(200, content=b"not json")],
    ids=["unreachable", "http-500", "malformed-body"],
)
async def test_when_core_fails_the_edge_returns_an_error_with_the_same_id(
    core_response: httpx.Response | None,
) -> None:
    rig = _build(_FailingCore(core_response))
    response = await _call(rig, {CORRELATION_HEADER: "fail-case-7"})
    assert response.status_code == 502
    assert response.headers[CORRELATION_HEADER] == "fail-case-7"
    assert response.json() == {"error": "core_unavailable", "correlation_id": "fail-case-7"}
    records = [json.loads(line) for line in rig.edge_log.getvalue().splitlines()]
    errors = [r for r in records if r["level"] == "ERROR"]
    assert errors and all(r["correlation_id"] == "fail-case-7" for r in errors)


@pytest.mark.anyio
async def test_the_edge_never_retries_a_failed_core_call() -> None:
    calls: list[str] = []

    class Counting(_FailingCore):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            return await super().handle_async_request(request)

    rig = _build(Counting(None))
    await _call(rig)
    assert calls == ["/echo"]


@pytest.mark.anyio
async def test_concurrent_requests_keep_their_own_ids() -> None:
    import asyncio

    rig = _build()
    ids = [f"req-{n}" for n in range(8)]
    responses = await asyncio.gather(*(_call(rig, {CORRELATION_HEADER: i}) for i in ids))
    assert [r.headers[CORRELATION_HEADER] for r in responses] == ids
    assert [r.json()["core_correlation_id"] for r in responses] == ids
