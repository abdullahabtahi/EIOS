"""FastAPI Enterprise Application Factory with CORS and Native SSE Support (F019 Phase 2, T005)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eios.api.routes_aml import router as aml_router
from eios.api.routes_churn import router as churn_router
from eios.api.routes_fraud import router as fraud_router
from eios.api.routes_ops import router as ops_router
from eios.api.routes_synthesis import router as synthesis_router
from eios.api.routes_webhooks import router as webhooks_router
from eios.cockpit import ambient_routes, copilot_verify, evidence_routes
from eios.cockpit import geo as geo_routes
from eios.cockpit.assistant_gateway import drain_sessions
from eios.cockpit.assistant_gateway import warm_up as warm_up_assistant
from eios.cockpit.auth import cors_origins, current_operator
from eios.cockpit.server import public_router as cockpit_public_router
from eios.cockpit.server import router as cockpit_router
from eios.dataplane.geo_plane import warm_graph
from eios.dataplane.plane import read_models
from eios.observability.cloud_trace import configure_cloud_trace

_LOG = logging.getLogger(__name__)
HEALTH_PATH = "/health"
API_HEALTH_PATH = "/api/health"


async def _warm_up_address_check() -> None:
    """Read the address-check snapshot into memory in the background, so the first lookup does not wait for it.

    It is not part of readiness: an instance answers everything else while this runs, and a lookup that arrives first
    simply waits for the same single read."""
    reader = geo_routes.get_net_reader()
    if reader is None:
        return
    try:
        await asyncio.to_thread(reader.snapshot)
    except Exception:
        _LOG.warning("the address-check snapshot could not be read at start-up; lookups will retry")


async def _prepare_briefs_after(warm_up: asyncio.Task[None]) -> None:
    """Once the assistant is warm, prepare the briefs for the top alerts (nothing when EIOS_AMBIENT_TOP_N is 0)."""
    await warm_up
    running = ambient_routes.start_refresh()
    if running is not None:
        await running


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Build the data plane before serving, then warm the assistant in the background.

    The engines take seconds to build and every route reads them. Built on first request, the first operator after a
    deploy or a scale-up waited for it, and the web proxy's short timeout turned that wait into a labelled replay. Built
    here, an instance is not ready until it can answer, and Cloud Run keeps sending traffic to the old revision until then.
    A failed build is logged and retried by the next request, so a start-up fault shows as real errors, not a crash loop."""
    # Before the first turn, so ADK's spans have a tracer provider and content stays off. In a thread: it reads
    # credentials and may call the metadata server.
    await asyncio.to_thread(configure_cloud_trace)
    try:
        await asyncio.to_thread(read_models)
    except Exception:
        _LOG.exception("the data plane could not be built at start-up; requests will retry")
    task = asyncio.create_task(warm_up_assistant())
    ambient_task = asyncio.create_task(_prepare_briefs_after(task))
    graph_task = asyncio.create_task(
        asyncio.to_thread(warm_graph)
    )  # the first graph job is the slow one
    address_task = asyncio.create_task(_warm_up_address_check())
    try:
        yield
    finally:
        task.cancel()
        ambient_task.cancel()
        graph_task.cancel()
        address_task.cancel()
        await drain_sessions()  # conversation events still held in memory are written before exit


def create_app() -> FastAPI:
    """Creates and configures the production-grade EIOS FastAPI application."""
    app = FastAPI(
        title="EIOS Enterprise Intelligence API",
        version="0.19.0",
        description="Unified Enterprise Intelligence Engine with native SSE streaming and strict sovereign governance",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Mount domain feature routers and Cockpit presentation router
    app.include_router(churn_router, dependencies=[Depends(current_operator)])
    app.include_router(fraud_router, dependencies=[Depends(current_operator)])
    app.include_router(aml_router, dependencies=[Depends(current_operator)])
    app.include_router(synthesis_router, dependencies=[Depends(current_operator)])
    app.include_router(webhooks_router)
    app.include_router(ops_router, dependencies=[Depends(current_operator)])
    app.include_router(cockpit_public_router)
    app.include_router(cockpit_router)
    app.include_router(geo_routes.router)  # carries its own operator dependency
    app.include_router(copilot_verify.router)  # likewise
    app.include_router(evidence_routes.router)  # likewise
    app.include_router(
        ambient_routes.router
    )  # prepared briefs; the routes carry their own dependencies

    @app.get(HEALTH_PATH)
    @app.get(API_HEALTH_PATH)
    def health_check() -> dict[str, Any]:
        now_str = datetime.now(UTC).isoformat()
        return {
            "status": "UP",
            "version": "0.19.0",
            "service": "EIOS Enterprise API Gateway",
            "engine": "EIOS Presentation & Intelligence Engine",
            "design_system": "EIOS Sovereign Design Tokens (Light Mode)",
            "security_standard": "Google Cloud KMS ECDSA P-256",
            "cors_configured": True,
            "sse_enabled": True,
            "as_of": now_str,
            "timestamp": now_str,
        }

    return app


app = create_app()
