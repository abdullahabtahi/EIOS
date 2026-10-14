"""FastAPI Enterprise Application Factory with CORS and Native SSE Support (F019 Phase 2, T005)."""

from __future__ import annotations

import asyncio
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
from eios.cockpit.assistant_gateway import warm_up as warm_up_assistant
from eios.cockpit.auth import cors_origins, current_operator
from eios.cockpit.server import public_router as cockpit_public_router
from eios.cockpit.server import router as cockpit_router

HEALTH_PATH = "/health"
API_HEALTH_PATH = "/api/health"


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Warm the assistant in the background so startup is not held up and the first turn is not slow."""
    task = asyncio.create_task(warm_up_assistant())
    try:
        yield
    finally:
        task.cancel()


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
