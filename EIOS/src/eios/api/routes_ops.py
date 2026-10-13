"""Data Platform Operations Board and DLQ Redrive API Routes (F019 Phase 7, T023)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from eios.cockpit.operations import DataPlatformOperationsService

router = APIRouter(tags=["Data Operations"])
ops_svc = DataPlatformOperationsService()

TELEMETRY_PATH = "/api/v1/ops/telemetry"
DLQ_PATH = "/api/v1/ops/dlq"
DLQ_REDRIVE_PATH = "/api/v1/ops/dlq/redrive"

# Mock DLQ storage
_DLQ_STORE: list[dict[str, Any]] = [
    {
        "dlq_id": "dlq_rec_90112",
        "source_stream": "kafka.raw.trade_events.v2",
        "error_category": "SCHEMA_VALIDATION_FAILED",
        "error_message": "Missing required field 'execution_price_usd'",
        "quarantined_at": datetime.now(UTC).isoformat(),
        "payload": {
            "account_id": "ACC-99210",
            "symbol": "XAUUSD",
            "volume_lots": 1.5,
            "nonce": "n_malformed_1",
        },
        "redrive_count": 0,
        "status": "QUARANTINED",
    },
    {
        "dlq_id": "dlq_rec_90113",
        "source_stream": "kafka.raw.kyc_profiles.v1",
        "error_category": "SIGNATURE_VERIFICATION_FAILED",
        "error_message": "IdP signature mismatch against public JWKS",
        "quarantined_at": datetime.now(UTC).isoformat(),
        "payload": {
            "client_id": "CR-SUSPECT-84920",
            "idp_provider": "SumSub",
            "status": "SUBMITTED",
        },
        "redrive_count": 0,
        "status": "QUARANTINED",
    },
]


class RedriveRequest(BaseModel):
    dlq_id: str = Field(..., description="Target quarantined DLQ record ID")
    sanitized_payload: dict[str, Any] | None = Field(
        None, description="Optional corrected payload fields"
    )


@router.get(TELEMETRY_PATH)
def get_ops_telemetry() -> dict[str, Any]:
    """Returns operational health, SLAs, and active alerts across all 6 core data products."""
    products = [p.to_contract_dict() for p in ops_svc.get_data_products()]
    alerts = ops_svc.get_contract_breach_alerts()
    conflicts = ops_svc.get_identity_cluster_conflicts()

    return {
        "as_of": datetime.now(UTC).isoformat(),
        "sla_freshness_target_seconds": 30,
        "total_data_products": len(products),
        "products": products,
        "breach_alerts": alerts,
        "identity_conflicts": conflicts,
        "quarantined_dlq_depth": len([r for r in _DLQ_STORE if r["status"] == "QUARANTINED"]),
    }


@router.get(DLQ_PATH)
def get_dlq_records() -> dict[str, Any]:
    """Returns quarantined Dead Letter Queue records for operator inspection."""
    return {
        "as_of": datetime.now(UTC).isoformat(),
        "total_quarantined": len(_DLQ_STORE),
        "records": _DLQ_STORE,
    }


@router.post(DLQ_REDRIVE_PATH)
def redrive_dlq_record(req: RedriveRequest) -> dict[str, Any]:
    """Redrives quarantined DLQ record back into live processing pipeline after schema repair."""
    target = next((r for r in _DLQ_STORE if r["dlq_id"] == req.dlq_id), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DLQ record '{req.dlq_id}' not found",
        )

    if req.sanitized_payload:
        target["payload"].update(req.sanitized_payload)

    target["redrive_count"] += 1
    target["status"] = "REDRIVEN_COMMITTED"
    target["redriven_at"] = datetime.now(UTC).isoformat()

    return {
        "status": "REDRIVE_SUCCESSFUL",
        "dlq_id": req.dlq_id,
        "redrive_count": target["redrive_count"],
        "redriven_at": target["redriven_at"],
    }
