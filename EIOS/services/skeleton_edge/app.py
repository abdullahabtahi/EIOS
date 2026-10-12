"""skeleton_edge: health plus one GET route that forwards a correlated call to skeleton_core.

The core address comes from ``EIOS_CORE_URL`` (required when no client is injected) and the
call timeout from ``EIOS_CORE_TIMEOUT_SECONDS``. A failed call is answered with an explicit
502 body carrying the correlation id; there is no retry, so a failure is never hidden.
Run with ``uvicorn --factory services.skeleton_edge.app:create_app``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from opentelemetry.trace import SpanKind

from eios.common.correlation import (
    MissingCorrelationError,
    current_id,
    is_valid_correlation_id,
    outbound_headers,
)
from eios.common.errors import ConfigError
from eios.common.http_correlation import ErrorBody, HealthResponse, install_correlation_middleware
from eios.common.otel import (
    Telemetry,
    inject_trace_headers,
    service_name_from_env,
    setup_telemetry,
)
from eios.common.validation import StrictModel

DEFAULT_SERVICE_NAME = "skeleton_edge"
ENV_CORE_URL = "EIOS_CORE_URL"
ENV_CORE_TIMEOUT = "EIOS_CORE_TIMEOUT_SECONDS"
DEFAULT_CORE_TIMEOUT_SECONDS = 2.0  # [ASSUMPTION] skeleton default, tuned by the owning feature
CORE_ECHO_PATH = "/echo"
CORE_UNAVAILABLE = "core_unavailable"


class CoreEcho(StrictModel):
    correlation_id: str


class ForwardResponse(StrictModel):
    correlation_id: str
    core_correlation_id: str


def _core_client_from_env(environ: Mapping[str, str]) -> httpx.AsyncClient:
    url = environ.get(ENV_CORE_URL, "").strip()
    if not url:
        raise ConfigError(ENV_CORE_URL, "value", "the skeleton_core address is required")
    raw = environ.get(ENV_CORE_TIMEOUT, str(DEFAULT_CORE_TIMEOUT_SECONDS))
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise ConfigError(ENV_CORE_TIMEOUT, "value", "must be a number of seconds") from exc
    if not 0 < timeout < float("inf"):
        raise ConfigError(ENV_CORE_TIMEOUT, "value", "must be greater than zero")
    return httpx.AsyncClient(base_url=url, timeout=timeout)


async def _call_core(client: httpx.AsyncClient, telemetry: Telemetry) -> str:
    """Call core once; return the id it echoed. Raises httpx.HTTPError or ValueError."""
    with telemetry.tracer.start_as_current_span("call skeleton_core", kind=SpanKind.CLIENT):
        headers = inject_trace_headers(outbound_headers({"Accept": "application/json"}))
        response = await client.get(CORE_ECHO_PATH, headers=headers)
        response.raise_for_status()
        echoed = CoreEcho.model_validate_json(response.content).correlation_id
    if not is_valid_correlation_id(echoed):
        raise ValueError("core returned a malformed correlation id")
    return echoed


def create_app(
    *,
    telemetry: Telemetry | None = None,
    core_client: httpx.AsyncClient | None = None,
    environ: Mapping[str, str] | None = None,
) -> FastAPI:
    """Build the app; ``telemetry`` and ``core_client`` are injected by tests."""
    env = os.environ if environ is None else environ
    resolved = telemetry or setup_telemetry(
        service_name_from_env(env, default=DEFAULT_SERVICE_NAME), environ=env
    )
    client = core_client or _core_client_from_env(env)
    owns_client = core_client is None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if owns_client:
            await client.aclose()

    app = FastAPI(
        title=DEFAULT_SERVICE_NAME,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    install_correlation_middleware(app, resolved)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/forward", response_model=ForwardResponse, responses={502: {"model": ErrorBody}})
    async def forward() -> ForwardResponse | JSONResponse:
        sent = current_id()
        if sent is None:
            raise MissingCorrelationError
        try:
            echoed = await _call_core(client, resolved)
        except (httpx.HTTPError, ValueError) as exc:
            resolved.logger.error("core call failed", extra={"cause": type(exc).__name__})
            body = ErrorBody(error=CORE_UNAVAILABLE, correlation_id=sent)
            return JSONResponse(body.model_dump(), status_code=502)
        return ForwardResponse(correlation_id=sent, core_correlation_id=echoed)

    return app
