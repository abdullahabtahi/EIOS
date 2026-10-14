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


class OpsTelemetryResponse(BaseModel):
    as_of: str = Field(..., description="Telemetry snapshot timestamp in ISO 8601 UTC")
    sla_freshness_target_seconds: int = Field(default=30, description="Freshness target in seconds")
    slo_met: bool = Field(
        default=True, description="Whether data products meet freshness SLA targets"
    )
    total_data_products: int = Field(..., description="Count of monitored data products")
    products: list[dict[str, Any]] = Field(..., description="Data product contract states")
    breach_alerts: list[dict[str, Any]] = Field(..., description="Active contract breach alerts")
    identity_conflicts: list[dict[str, Any]] = Field(..., description="Identity cluster conflicts")
    quarantined_dlq_depth: int = Field(..., description="Current count of quarantined DLQ records")


class DlqRecordsResponse(BaseModel):
    as_of: str = Field(..., description="Snapshot timestamp in ISO 8601 UTC")
    total_quarantined: int = Field(..., description="Count of quarantined DLQ records")
    records: list[dict[str, Any]] = Field(..., description="Quarantined records list")


class RedriveRequest(BaseModel):
    dlq_id: str = Field(..., description="Target quarantined DLQ record ID")
    sanitized_payload: dict[str, Any] | None = Field(
        None, description="Optional corrected payload fields"
    )


class RedriveResponse(BaseModel):
    status: str = Field(default="REDRIVE_SUCCESSFUL", description="Redrive operation status")
    dlq_id: str = Field(..., description="Quarantined record ID")
    redrive_count: int = Field(..., description="Total redrive attempts count")
    redriven_at: str = Field(..., description="Redrive execution timestamp in ISO 8601 UTC")


@router.get(TELEMETRY_PATH, response_model=OpsTelemetryResponse)
def get_ops_telemetry() -> OpsTelemetryResponse:
    """Returns operational health, SLAs, and active alerts across all 6 core data products."""
    products = [p.to_contract_dict() for p in ops_svc.get_data_products()]
    alerts = ops_svc.get_contract_breach_alerts()
    conflicts = ops_svc.get_identity_cluster_conflicts()

    return OpsTelemetryResponse(
        as_of=datetime.now(UTC).isoformat(),
        sla_freshness_target_seconds=30,
        slo_met=True,
        total_data_products=len(products),
        products=products,
        breach_alerts=alerts,
        identity_conflicts=conflicts,
        quarantined_dlq_depth=len([r for r in _DLQ_STORE if r["status"] == "QUARANTINED"]),
    )


@router.get(DLQ_PATH, response_model=DlqRecordsResponse)
def get_dlq_records() -> DlqRecordsResponse:
    """Returns quarantined Dead Letter Queue records for operator inspection."""
    return DlqRecordsResponse(
        as_of=datetime.now(UTC).isoformat(),
        total_quarantined=len(_DLQ_STORE),
        records=_DLQ_STORE,
    )


@router.post(DLQ_REDRIVE_PATH, response_model=RedriveResponse)
def redrive_dlq_record(req: RedriveRequest) -> RedriveResponse:
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

    return RedriveResponse(
        status="REDRIVE_SUCCESSFUL",
        dlq_id=req.dlq_id,
        redrive_count=target["redrive_count"],
        redriven_at=target["redriven_at"],
    )
