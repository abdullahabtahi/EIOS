"""FastAPI Enterprise Application Factory with CORS and Native SSE Support (F019 Phase 2, T005)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eios.api.routes_churn import router as churn_router
from eios.api.routes_fraud import router as fraud_router
from eios.api.routes_aml import router as aml_router
from eios.api.routes_synthesis import router as synthesis_router
from eios.api.routes_webhooks import router as webhooks_router
from eios.api.routes_ops import router as ops_router
from eios.cockpit.server import router as cockpit_router

HEALTH_PATH = "/health"
API_HEALTH_PATH = "/api/health"


def create_app() -> FastAPI:
    """Creates and configures the production-grade EIOS FastAPI application."""
    app = FastAPI(
        title="EIOS Enterprise Intelligence API",
        version="0.19.0",
        description="Unified Enterprise Intelligence Engine with native SSE streaming and strict sovereign governance",
    )

    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount domain feature routers and Cockpit presentation router
    app.include_router(churn_router)
    app.include_router(fraud_router)
    app.include_router(aml_router)
    app.include_router(synthesis_router)
    app.include_router(webhooks_router)
    app.include_router(ops_router)
    app.include_router(cockpit_router)

    @app.get(HEALTH_PATH)
    @app.get(API_HEALTH_PATH)
    def health_check() -> Dict[str, Any]:
        return {
            "status": "UP",
            "version": "0.19.0",
            "service": "EIOS Enterprise API Gateway",
            "cors_configured": True,
            "sse_enabled": True,
            "as_of": datetime.now(UTC).isoformat(),
        }

    return app


app = create_app()
