"""Dead-Letter Queue (DLQ) envelope builder, dispatcher, and structured Cloud Logging emitter."""

import base64
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from eios.contracts.base import DataProductEnum

logger = logging.getLogger("eios.ingestion.dlq")


class BreachType(str, Enum):
    """Categorical typology of validation failure."""

    SCHEMA_TYPE_ERROR = "SCHEMA_TYPE_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    NULL_RATE_EXCEEDED = "NULL_RATE_EXCEEDED"
    VALUE_RANGE_VIOLATION = "VALUE_RANGE_VIOLATION"
    UNSANITIZED_PAYLOAD = "UNSANITIZED_PAYLOAD"
    CORRUPTED_SERIALIZATION = "CORRUPTED_SERIALIZATION"


@dataclass
class ContractBreachRecord:
    """Standardized Dead-Letter Queue envelope matching schemas/dlq-envelope.schema.json."""

    dlq_id: str
    event_id: str
    product_name: DataProductEnum
    breach_timestamp: datetime
    breach_type: BreachType
    field_paths: list[str]
    error_messages: list[str]
    raw_payload_bytes: str  # base64 encoded string
    source_topic: str
    ingestion_metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict matching dlq-envelope.schema.json specification."""
        out = {
            "dlq_id": self.dlq_id,
            "event_id": self.event_id,
            "product_name": self.product_name.value
            if isinstance(self.product_name, DataProductEnum)
            else str(self.product_name),
            "breach_timestamp": self.breach_timestamp.isoformat(),
            "breach_type": self.breach_type.value
            if isinstance(self.breach_type, BreachType)
            else str(self.breach_type),
            "field_paths": self.field_paths,
            "error_messages": self.error_messages,
            "raw_payload_bytes": self.raw_payload_bytes,
            "source_topic": self.source_topic,
        }
        if self.ingestion_metadata:
            out["ingestion_metadata"] = self.ingestion_metadata
        return out


class DLQDispatcher:
    """Buffers, logs, and dispatches contract breaches to eios.l1.dlq.v1 with zero silent drops."""

    def __init__(self, dlq_topic: str = "eios.l1.dlq.v1") -> None:
        self.dlq_topic = dlq_topic
        self._buffer: list[ContractBreachRecord] = []

    def create_breach_record(
        self,
        product_name: DataProductEnum,
        raw_payload: Any,
        errors: list[dict[str, Any]],
        breach_type: BreachType = BreachType.SCHEMA_TYPE_ERROR,
        source_topic: str = "",
        event_id: str | None = None,
        ingestion_metadata: dict[str, Any] | None = None,
    ) -> ContractBreachRecord:
        """Construct a standardized DLQ envelope from raw payload and validation errors."""
        # Convert raw payload to base64 bytes
        if isinstance(raw_payload, bytes):
            raw_bytes = raw_payload
        else:
            raw_bytes = json.dumps(raw_payload, default=str).encode("utf-8")
        raw_b64 = base64.b64encode(raw_bytes).decode("ascii")

        field_paths = []
        error_msgs = []
        for err in errors:
            loc = err.get("loc") or err.get("field_path") or ()
            if isinstance(loc, (list, tuple)):
                field_paths.append(".".join(str(item) for item in loc))
            else:
                field_paths.append(str(loc))
            error_msgs.append(err.get("msg") or err.get("message") or "Unknown validation error")

        record = ContractBreachRecord(
            dlq_id=str(uuid4()),
            event_id=event_id or f"evt_syn_{uuid4().hex[:12]}",
            product_name=product_name,
            breach_timestamp=datetime.now(UTC),
            breach_type=breach_type,
            field_paths=field_paths,
            error_messages=error_msgs,
            raw_payload_bytes=raw_b64,
            source_topic=source_topic
            or f"eios.l1.{product_name.value if isinstance(product_name, DataProductEnum) else product_name}.v1",
            ingestion_metadata=ingestion_metadata,
        )

        self._buffer.append(record)

        # Structured Cloud Logging JSON (Principle IV)
        log_payload = {
            "severity": "WARNING",
            "message": f"Contract breach intercepted for product {product_name}: {breach_type.value}",
            "dlq_record": record.to_dict(),
        }
        logger.warning(json.dumps(log_payload))

        return record

    def get_pending_count(self) -> int:
        return len(self._buffer)

    def flush(self) -> list[ContractBreachRecord]:
        """Flush buffer for publishing to Pub/Sub DLQ sink."""
        records = list(self._buffer)
        self._buffer.clear()
        return records
