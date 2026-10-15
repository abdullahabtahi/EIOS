"""Accepted events and quarantined breaches as warehouse rows: the contract's fields plus the lineage columns."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from eios.contracts.base import DataProductEvent
from eios.ingestion.dlq import ContractBreachRecord


def _json_safe(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime | date) else value


def event_rows(
    events: Iterable[DataProductEvent], *, batch_id: str, source: str, loaded_at: datetime
) -> list[dict[str, Any]]:
    """One row per accepted event. The payload is what the contract validated (and the vault already pseudonymised)."""
    stamp = loaded_at.isoformat()
    return [
        {
            **{k: _json_safe(v) for k, v in e.payload.items()},
            "_batch_id": batch_id,
            "_loaded_at": stamp,
            "_source": source,
            "_tenant_id": e.tenant_id.value,
        }
        for e in events
    ]


def breach_rows(
    records: Iterable[ContractBreachRecord], *, batch_id: str, source: str, loaded_at: datetime
) -> list[dict[str, Any]]:
    """One row per quarantined event: why it broke the contract, and a hash of the raw payload (never the payload)."""
    stamp = loaded_at.isoformat()
    return [
        {
            "dlq_id": r.dlq_id,
            "event_id": r.event_id,
            "product_name": r.product_name.value,
            "breach_type": getattr(r.breach_type, "value", str(r.breach_type)),
            "field_paths": list(r.field_paths),
            "error_messages": list(r.error_messages),
            "payload_sha256": hashlib.sha256(r.raw_payload_bytes.encode()).hexdigest(),
            "breach_timestamp": r.breach_timestamp.isoformat(),
            "_batch_id": batch_id,
            "_loaded_at": stamp,
            "_source": source,
            "_tenant_id": (r.ingestion_metadata or {}).get("tenant_id"),
        }
        for r in records
    ]
