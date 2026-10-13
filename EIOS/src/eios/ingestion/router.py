"""FastAPI Ingestion Gateway application, endpoints, and health probes."""

import asyncio
import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from eios.contracts.base import DataProductEnum, DataProductEvent
from eios.ingestion.circuit_breaker import IngestionCircuitBreaker
from eios.ingestion.config import IngestionConfig, get_ingestion_config
from eios.ingestion.dlq import DLQDispatcher
from eios.ingestion.dq import DQMonitor
from eios.ingestion.exporter import ParquetLakehouseExporter
from eios.ingestion.hot_state import HotStateEngine
from eios.ingestion.processor import IngestionPipeline
from eios.ingestion.queue import IngestionQueue, get_ingestion_queue
from eios.ingestion.subscriber import IngestionSubscriber
from eios.ingestion.validator import ContractValidator
from eios.ingestion.vault import TokenVault
from eios.ingestion.warm_start import ParquetWarmStartLoader

logger = logging.getLogger("eios.ingestion.router")

# Map of data product to timestamp column for sliding window eviction
TIMESTAMP_COLUMNS: dict[DataProductEnum, str] = {
    DataProductEnum.CLIENT_360: "kyc_approved_at",
    DataProductEnum.CLIENT_FUNNEL: "entered_at",
    DataProductEnum.TRANSACTIONS_AML: "timestamp",
    DataProductEnum.TRADING_ACTIVITY: "open_ts",
    DataProductEnum.DEVICE_NETWORK_GRAPH: "last_seen",
    DataProductEnum.COMMISSION_LEDGER: "paid_at",
    DataProductEnum.PARTNER_COMMS: "timestamp",
    DataProductEnum.COMPLIANCE_CASES: "created_at",
}


async def _drain_worker(app: FastAPI, flush_interval: float = 0.5) -> None:
    """Continuously drain micro-batch staging queue and export to Parquet lakehouse."""
    while True:
        try:
            await asyncio.sleep(flush_interval)
            events = app.state.queue.drain_batch(max_items=250)
            if not events:
                continue

            # Group events by product
            grouped: dict[DataProductEnum, list[dict[str, Any]]] = defaultdict(list)
            for evt in events:
                grouped[evt.product_name].append(evt.payload)

            for prod, records in grouped.items():
                try:
                    app.state.exporter.export_batch(prod, records)
                except Exception as exc:
                    logger.error(
                        "Failed to export lakehouse batch for %s: %s", prod, exc, exc_info=True
                    )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Error in background drain worker: %s", exc)


async def _eviction_worker(app: FastAPI, check_interval: float = 3600.0) -> None:
    """Periodically execute sliding-window eviction of expired hot-state telemetry."""
    while True:
        try:
            await asyncio.sleep(check_interval)
            for prod, ts_col in TIMESTAMP_COLUMNS.items():
                try:
                    app.state.hot_state.evict_older_than(prod, ts_col, hours=24)
                except Exception as exc:
                    logger.warning("Eviction skipped for product %s: %s", prod, exc)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Error in background eviction worker: %s", exc)


def create_ingestion_app(  # noqa: C901, PLR0913, PLR0915
    config: IngestionConfig | None = None,
    queue: IngestionQueue | None = None,
    validator: ContractValidator | None = None,
    dlq_dispatcher: DLQDispatcher | None = None,
    circuit_breaker: IngestionCircuitBreaker | None = None,
    hot_state: HotStateEngine | None = None,
    vault: TokenVault | None = None,
    dq_monitor: DQMonitor | None = None,
    pipeline: IngestionPipeline | None = None,
    exporter: ParquetLakehouseExporter | None = None,
) -> FastAPI:
    """Create and configure the FastAPI Ingestion Application."""
    app_config = config or get_ingestion_config()
    app_queue = queue or get_ingestion_queue()
    app_validator = validator or ContractValidator()
    app_dlq = dlq_dispatcher or DLQDispatcher(dlq_topic=app_config.dlq_topic_id)
    app_cb = circuit_breaker or IngestionCircuitBreaker()
    app_hot_state = hot_state or HotStateEngine()
    salt_bytes = getattr(
        app_config, "token_vault_salt", "deriv-eios-dev-salt-32bytes-secret"
    ).encode("utf-8")
    app_vault = vault or TokenVault(master_salt=salt_bytes)
    app_dq = dq_monitor or DQMonitor()

    app_pipeline = pipeline or IngestionPipeline(
        config=app_config,
        validator=app_validator,
        dlq_dispatcher=app_dlq,
        circuit_breaker=app_cb,
        hot_state=app_hot_state,
        vault=app_vault,
        dq_monitor=app_dq,
        queue=app_queue,
    )

    app_exporter = exporter or ParquetLakehouseExporter(
        export_base_dir=app_config.warm_start_data_path
    )
    subscriber = IngestionSubscriber(config=app_config, queue=app_queue, pipeline=app_pipeline)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: execute warm-start rehydration from lakehouse snapshots
        app.state.is_ready = False
        loader = ParquetWarmStartLoader(
            engine=app.state.hot_state,
            base_dir=app.state.config.warm_start_data_path,
        )
        summary = loader.load_all()
        app.state.warm_start_duration_ms = summary.load_duration_ms
        app.state.is_ready = True
        subscriber.start()

        # Start background workers
        drain_task = asyncio.create_task(_drain_worker(app))
        eviction_task = asyncio.create_task(_eviction_worker(app))
        yield
        # Shutdown: cancel workers and drain remaining events
        drain_task.cancel()
        eviction_task.cancel()
        subscriber.stop()

        # Final queue flush
        remaining = app.state.queue.drain_batch(max_items=10000)
        if remaining:
            grouped = defaultdict(list)
            for evt in remaining:
                grouped[evt.product_name].append(evt.payload)
            for prod, records in grouped.items():
                try:
                    app.state.exporter.export_batch(prod, records)
                except Exception:  # noqa: S110
                    pass

    app = FastAPI(
        title="Deriv EIOS Layer 1 Contract Gateway & Ingestion API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.config = app_config
    app.state.queue = app_queue
    app.state.validator = app_validator
    app.state.dlq = app_dlq
    app.state.circuit_breaker = app_cb
    app.state.hot_state = app_hot_state
    app.state.vault = app_vault
    app.state.dq_monitor = app_dq
    app.state.pipeline = app_pipeline
    app.state.exporter = app_exporter
    app.state.is_ready = True
    app.state.warm_start_duration_ms = 0.0

    def _mount_route(
        app_obj: FastAPI, path_str: str, handler: Any, http_methods: list[str], **kwargs: Any
    ) -> None:
        app_obj.add_api_route(path_str, handler, methods=http_methods, **kwargs)

    async def healthz():
        """Liveness probe: verifies container and event loop are responsive."""
        return {"status": "LIVE"}

    async def readyz():
        """Readiness probe: verifies hot-state warm start is complete."""
        if not getattr(app.state, "is_ready", False):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "INITIALIZING", "message": "Hot-state rehydration in progress"},
            )
        return {
            "status": "READY",
            "warm_start_duration_ms": getattr(app.state, "warm_start_duration_ms", 0.0),
        }

    async def dq_status():
        """Real-time Data Quality & Freshness SLA monitoring board."""
        return app.state.dq_monitor.get_all_statuses(circuit_breaker=app.state.circuit_breaker)

    async def ingest_events(events_input: DataProductEvent | list[DataProductEvent]):
        """Synchronously receive, validate, and buffer events into staging queue or DLQ."""
        if isinstance(events_input, list):
            events = events_input
        else:
            events = [events_input]

        batch_res = app.state.pipeline.process_batch(events)

        return {
            "status": batch_res.status,
            "accepted_count": batch_res.accepted_count,
            "rejected_count": batch_res.rejected_count,
            "receipt_id": batch_res.receipt_id,
            "breach_summary": batch_res.breach_summary,
        }

    _mount_route(app, "/healthz", healthz, ["GET"], tags=["Health"])
    _mount_route(app, "/readyz", readyz, ["GET"], tags=["Health"])
    _mount_route(app, "/v1/dq/status", dq_status, ["GET"], tags=["Data Quality"])
    _mount_route(
        app,
        "/v1/events/ingest",
        ingest_events,
        ["POST"],
        status_code=status.HTTP_202_ACCEPTED,
        tags=["Ingestion"],
    )

    return app
