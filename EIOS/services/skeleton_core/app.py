"""skeleton_core: health plus one GET route that echoes the correlation id it received (FR-036).

No mutation endpoint, no business metric, no product API (constitution II, ADR-014 open).
Run with ``uvicorn --factory services.skeleton_core.app:create_app``; the service name comes
from ``EIOS_SERVICE_NAME`` and telemetry from ``EIOS_OTEL_EXPORTER_ENDPOINT``.
"""

from __future__ import annotations

from fastapi import FastAPI

from eios.common.correlation import MissingCorrelationError, current_id
from eios.common.http_correlation import HealthResponse, install_correlation_middleware
from eios.common.otel import Telemetry, service_name_from_env, setup_telemetry
from eios.common.validation import StrictModel

DEFAULT_SERVICE_NAME = "skeleton_core"


class EchoResponse(StrictModel):
    correlation_id: str


def create_app(*, telemetry: Telemetry | None = None) -> FastAPI:
    """Build the app; ``telemetry`` is injected by tests, otherwise read from the environment."""
    resolved = telemetry or setup_telemetry(service_name_from_env(default=DEFAULT_SERVICE_NAME))
    app = FastAPI(title=DEFAULT_SERVICE_NAME, docs_url=None, redoc_url=None, openapi_url=None)
    install_correlation_middleware(app, resolved)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/echo", response_model=EchoResponse)
    async def echo() -> EchoResponse:
        bound = current_id()
        if bound is None:
            raise MissingCorrelationError
        return EchoResponse(correlation_id=bound)

    return app
