"""Cashier Webhook Listener & In-Line Sentinel Interception (F019 Phase 4, T014–T015)."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from eios.aml.models import WithdrawalDisposition
from eios.aml.withdrawal_sentinel import WithdrawalSentinel
from eios.ontology.actions.record_store import default_record_store

router = APIRouter(tags=["Webhooks"])
sentinel = WithdrawalSentinel()

CASHIER_WITHDRAWAL_PATH = "/api/v1/webhooks/cashier/withdrawal"
# Not a credential: a fixed value so local tests can sign requests. Deployed environments must supply
# the real secret (from Secret Manager) or the service refuses to start.
_DEV_WEBHOOK_SECRET = b"dev-only-webhook-secret"


def _load_webhook_secret() -> bytes:
    secret = os.environ.get("EIOS_CASHIER_WEBHOOK_SECRET")
    if secret:
        return secret.encode("utf-8")
    environment = os.environ.get("EIOS_ENVIRONMENT", "dev")
    if environment in {"dev", "test"}:
        return _DEV_WEBHOOK_SECRET
    raise RuntimeError(
        f"EIOS_CASHIER_WEBHOOK_SECRET must be set in the '{environment}' environment"
    )


WEBHOOK_SECRET = _load_webhook_secret()

# Durable replay attack prevention store (atomic create-if-absent, backed by Firestore in prod-like)
_NONCE_STORE = default_record_store("webhook_nonces")
# Process-local cache for fast path and test inspection backward compatibility
PROCESSED_NONCES: set[str] = set()


class CashierWithdrawalPayload(BaseModel):
    withdrawal_id: str = Field(..., description="Unique payment transaction reference")
    client_id: str = Field(..., description="Target client / account ID")
    amount_usd: float = Field(..., gt=0, description="Requested withdrawal amount in USD")
    payment_method: str = Field(default="USDT_ERC20", description="Payment gateway method")
    nonce: str = Field(..., description="Cryptographic unique request nonce")
    timestamp: int = Field(..., description="Unix epoch timestamp in milliseconds")
    hours_since_deposit: float = Field(default=72.0, ge=0)
    recent_alert_score: float = Field(default=0.20, ge=0, le=1.0)
    market_risk_pct: float = Field(default=0.15, ge=0)


class CashierWithdrawalResponse(BaseModel):
    status: str = Field(default="PROCESSED", description="Processing lifecycle state")
    withdrawal_id: str = Field(..., description="Unique payment transaction reference")
    client_id: str = Field(..., description="Target client / account ID")
    disposition: str = Field(..., description="Inline sentinel disposition: RELEASE or HOLD")
    composite_risk_score: float = Field(..., description="Sentinel composite risk score [0.0, 1.0]")
    decision_rationale: str = Field(..., description="Auditable reasoning behind the disposition")
    evaluation_latency_ms: float = Field(..., description="Evaluation latency in milliseconds")
    sla_met: bool = Field(..., description="Whether execution finished within the 150ms SLA")
    action_intent_id: str | None = Field(
        default=None, description="Action intent token if staged/held"
    )
    evaluated_at: str = Field(..., description="Evaluation timestamp in ISO 8601 UTC format")


def verify_hmac_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verifies HMAC SHA-256 signature against cashier shared secret."""
    if not signature_header:
        return False
    # Support both raw hex or sha256=hex format
    expected_hex = signature_header.replace("sha256=", "").strip()
    computed_hex = hmac.new(WEBHOOK_SECRET, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hex, computed_hex)


@router.post(CASHIER_WITHDRAWAL_PATH, response_model=CashierWithdrawalResponse)
async def handle_cashier_withdrawal_webhook(
    request: Request,
    x_signature_sha256: str | None = Header(None, alias="X-Signature-SHA256"),
    x_cashier_signature: str | None = Header(None, alias="X-Cashier-Signature"),
) -> CashierWithdrawalResponse:
    """In-line webhook interceptor returning pre-settlement HOLD / RELEASE decision in < 150ms."""
    start_time = time.perf_counter()
    raw_body = await request.body()

    signature = x_signature_sha256 or x_cashier_signature
    if not verify_hmac_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC SHA-256 signature on cashier withdrawal webhook",
        )

    try:
        import json

        body_dict = json.loads(raw_body.decode("utf-8"))
        payload = CashierWithdrawalPayload(**body_dict)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed webhook payload: {str(exc)}",
        ) from exc

    # Distributed Replay Attack Prevention: atomic create-if-absent across all instances
    created = _NONCE_STORE.create(
        payload.nonce,
        {
            "nonce": payload.nonce,
            "withdrawal_id": payload.withdrawal_id,
            "client_id": payload.client_id,
            "processed_at": datetime.now(UTC).isoformat(),
        },
    )
    if not created or payload.nonce in PROCESSED_NONCES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Replay attack detected: nonce '{payload.nonce}' has already been processed",
        )
    PROCESSED_NONCES.add(payload.nonce)

    # In-Line Sentinel Evaluation (< 150ms budget)
    assessment = sentinel.evaluate_withdrawal(
        withdrawal_id=payload.withdrawal_id,
        client_id=payload.client_id,
        amount_usd=payload.amount_usd,
        recent_alert_score=payload.recent_alert_score,
        hours_since_deposit=payload.hours_since_deposit,
        market_risk_pct=payload.market_risk_pct,
    )

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    disposition_str = (
        "RELEASE" if assessment.recommendation == WithdrawalDisposition.ALLOW else "HOLD"
    )

    return CashierWithdrawalResponse(
        status="PROCESSED",
        withdrawal_id=payload.withdrawal_id,
        client_id=payload.client_id,
        disposition=disposition_str,
        composite_risk_score=assessment.risk_score,
        decision_rationale=f"Sentinel evaluated risk {assessment.risk_score:.2f} ({assessment.recommendation.value})",
        evaluation_latency_ms=elapsed_ms,
        sla_met=elapsed_ms <= 150.0,
        action_intent_id=assessment.intent_id,
        evaluated_at=datetime.now(UTC).isoformat(),
    )
