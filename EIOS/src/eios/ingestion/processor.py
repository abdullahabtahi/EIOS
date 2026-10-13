"""Unified Ingestion Pipeline core shared across HTTP Push and Pub/Sub Pull ingress."""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from eios.contracts.base import DataProductEvent
from eios.ingestion.circuit_breaker import IngestionCircuitBreaker
from eios.ingestion.config import IngestionConfig, get_ingestion_config
from eios.ingestion.dlq import BreachType, DLQDispatcher
from eios.ingestion.dq import DQMonitor
from eios.ingestion.hot_state import HotStateEngine
from eios.ingestion.queue import IngestionQueue, get_ingestion_queue
from eios.ingestion.validator import ContractValidator, ValidationErrorDetail
from eios.ingestion.vault import TokenVault, resolve_master_salt

logger = logging.getLogger("eios.ingestion.processor")


@dataclass
class IngestionEventResult:
    """Result of processing a single operational telemetry event."""

    is_accepted: bool
    event: DataProductEvent | None = None
    dlq_id: str | None = None
    errors: list[ValidationErrorDetail] = field(default_factory=list)


@dataclass
class IngestionBatchResult:
    """Aggregated batch ingestion summary."""

    status: str
    accepted_count: int
    rejected_count: int
    receipt_id: str
    breach_summary: list[dict[str, Any]] = field(default_factory=list)


class IngestionPipeline:
    """Unified telemetry processing engine enforcing contracts, privacy, DQ, and hot state."""

    def __init__(  # noqa: PLR0913
        self,
        config: IngestionConfig | None = None,
        validator: ContractValidator | None = None,
        dlq_dispatcher: DLQDispatcher | None = None,
        circuit_breaker: IngestionCircuitBreaker | None = None,
        hot_state: HotStateEngine | None = None,
        vault: TokenVault | None = None,
        dq_monitor: DQMonitor | None = None,
        queue: IngestionQueue | None = None,
    ) -> None:
        self.config = config or get_ingestion_config()
        self.validator = validator or ContractValidator()
        self.dlq_dispatcher = dlq_dispatcher or DLQDispatcher(dlq_topic=self.config.dlq_topic_id)
        self.circuit_breaker = circuit_breaker or IngestionCircuitBreaker()
        self.hot_state = hot_state or HotStateEngine()
        self.vault = vault or TokenVault(master_salt=resolve_master_salt(self.config.hmac_salt))
        self.dq_monitor = dq_monitor or DQMonitor()
        self.queue = queue or get_ingestion_queue()

    def process_event(self, event: DataProductEvent) -> IngestionEventResult:
        """Process an individual event through full governance lifecycle."""
        val_res = self.validator.validate(event.product_name, event.payload)

        if not val_res.is_valid:
            self.circuit_breaker.record_breach(event.product_name)
            breach_record = self.dlq_dispatcher.create_breach_record(
                product_name=event.product_name,
                raw_payload=event.payload,
                errors=[
                    {"loc": err.field_path.split("."), "msg": err.message} for err in val_res.errors
                ],
                breach_type=BreachType.SCHEMA_TYPE_ERROR,
                source_topic=f"eios.l1.{event.product_name.value}.v1",
                event_id=str(event.event_id),
                ingestion_metadata={"tenant_id": event.tenant_id.value},
            )
            return IngestionEventResult(
                is_accepted=False,
                event=event,
                dlq_id=breach_record.dlq_id,
                errors=val_res.errors,
            )

        # 1. Record healthy contract metric
        self.circuit_breaker.record_success(event.product_name)

        # 2. Record Data Quality freshness and null rate statistics
        self.dq_monitor.record_event(
            event.product_name,
            event.event_timestamp,
            event.payload,
        )

        # 3. Deterministically pseudonymize Marking P attributes before hot state / queue
        sanitized_payload = self.vault.pseudonymize_payload(event.product_name, event.payload)
        event.payload = sanitized_payload

        # 4. Insert into in-memory hot state
        try:
            self.hot_state.insert_event(event.product_name, sanitized_payload)
        except Exception as exc:
            logger.error(
                "Hot-state insertion error for event %s (product=%s): %s",
                event.event_id,
                event.product_name,
                exc,
                exc_info=True,
            )

        # 5. Buffer into bounded staging queue
        self.queue.push(event)

        return IngestionEventResult(is_accepted=True, event=event)

    def process_batch(self, events: list[DataProductEvent]) -> IngestionBatchResult:
        """Process a batch of events with aggregated breach reporting."""
        receipt_id = f"rcpt_{uuid4().hex[:12]}"
        accepted_count = 0
        breach_summary = []

        for event in events:
            res = self.process_event(event)
            if res.is_accepted:
                accepted_count += 1
            else:
                breach_summary.append(
                    {
                        "event_id": str(event.event_id),
                        "product_name": event.product_name.value,
                        "dlq_id": res.dlq_id,
                        "errors": [err.message for err in res.errors],
                    }
                )

        return IngestionBatchResult(
            status="ACCEPTED",
            accepted_count=accepted_count,
            rejected_count=len(breach_summary),
            receipt_id=receipt_id,
            breach_summary=breach_summary,
        )
