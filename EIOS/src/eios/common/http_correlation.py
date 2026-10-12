"""Shared HTTP plumbing for service skeletons (FR-036): correlation middleware and tiny models.

``install_correlation_middleware`` makes every request:
1. resolve the correlation id (inbound header kept only if valid, else replaced),
2. bind it to the task, continue the caller's W3C trace (or start a root trace),
3. open a server span, log one line, and echo the id in the response header,
4. turn an unhandled error into a 500 body that carries the same id (never the error text).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from opentelemetry.trace import SpanKind, Status, StatusCode

from eios.common.correlation import CORRELATION_HEADER, correlation_scope, resolve_inbound_id
from eios.common.otel import Telemetry, extract_trace_context
from eios.common.validation import StrictModel

INTERNAL_ERROR = "internal_error"


class HealthResponse(StrictModel):
    status: str = "ok"


class ErrorBody(StrictModel):
    error: str
    correlation_id: str


async def _handle(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    telemetry: Telemetry,
    correlation_id: str,
) -> Response:
    try:
        response = await call_next(request)
    except Exception:
        telemetry.logger.exception(
            "unhandled error", extra={"method": request.method, "path": request.url.path}
        )
        body = ErrorBody(error=INTERNAL_ERROR, correlation_id=correlation_id)
        return JSONResponse(body.model_dump(), status_code=500)
    telemetry.logger.info(
        "request handled",
        extra={"method": request.method, "path": request.url.path, "status": response.status_code},
    )
    return response


def install_correlation_middleware(app: FastAPI, telemetry: Telemetry) -> None:
    """Register the correlation, tracing and request-log middleware on ``app``."""

    @app.middleware("http")
    async def correlate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = resolve_inbound_id(request.headers.get(CORRELATION_HEADER))
        parent = extract_trace_context(request.headers)
        with (
            correlation_scope(correlation_id),
            telemetry.tracer.start_as_current_span(
                f"{request.method} {telemetry.service_name}", context=parent, kind=SpanKind.SERVER
            ) as span,
        ):
            response = await _handle(request, call_next, telemetry, correlation_id)
            span.set_attribute("http.response.status_code", response.status_code)
            if response.status_code >= 500:
                span.set_status(Status(StatusCode.ERROR))
            response.headers[CORRELATION_HEADER] = correlation_id
            return response
