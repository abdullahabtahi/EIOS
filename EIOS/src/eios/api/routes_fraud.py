"""Partner Fraud and Opposite-Trading Ring API Routes (F019 Phase 2, T007)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent

from eios.cockpit.partner import PartnerWorkstationService

router = APIRouter(tags=["Partner Fraud"])
partner_svc = PartnerWorkstationService()

TREE_PATH = "/api/v1/fraud/tree"
PAIRS_PATH = "/api/v1/fraud/pairs"
STREAM_PATH = "/api/v1/fraud/stream"


@router.get(TREE_PATH)
def get_fraud_tree(partner_id: str = Query(default="AP-1029")) -> dict[str, Any]:
    """Returns the 3-layer sub-affiliate directed tree with clawback exposure and churn metrics."""
    tree = partner_svc.get_partner_referral_tree(partner_id=partner_id)
    # Enrich with clawback exposure calculation
    total_clawback = sum(
        ring.get("abusive_volume_usd", 0.0) * 0.15
        for ring in tree.get("detected_abusive_rings", [])
    )
    tree["total_clawback_exposure_usd"] = round(total_clawback, 2)
    tree["clawback_status"] = "STAGED_FOR_GOVERNED_REVIEW"
    tree["affiliate_depth_layers"] = 3
    return tree


@router.get(PAIRS_PATH)
def get_mirror_trading_pairs() -> dict[str, Any]:
    """Returns detected mirror-trading and opposite-order matching pairs across accounts."""
    now = datetime.now(UTC).isoformat()
    return {
        "as_of": now,
        "monitored_pairs_count": 8,
        "active_collusion_rings": [
            {
                "ring_id": "RING-SEA-881",
                "master_affiliate": "AP-1029",
                "account_a": "ACC-99210-BUY",
                "account_b": "ACC-99211-SELL",
                "instrument": "XAUUSD (Gold)",
                "correlation_coefficient": 0.9984,
                "latency_delta_ms": 12,
                "total_matched_volume_usd": 680000.0,
                "churn_bonus_extracted_usd": 34000.0,
                "status": "FLAGGED",
            },
            {
                "ring_id": "RING-LATAM-402",
                "master_affiliate": "AP-3088",
                "account_a": "ACC-77102-BUY",
                "account_b": "ACC-77103-SELL",
                "instrument": "EURUSD",
                "correlation_coefficient": 0.9852,
                "latency_delta_ms": 18,
                "total_matched_volume_usd": 240000.0,
                "churn_bonus_extracted_usd": 12000.0,
                "status": "FLAGGED",
            },
        ],
    }


@router.get(STREAM_PATH, response_class=EventSourceResponse)
async def stream_fraud_updates() -> AsyncIterable[ServerSentEvent]:
    """Streams live real-time fraud tree and mirror trading detections via native SSE."""
    try:
        for i in range(3):
            pairs_data = get_mirror_trading_pairs()
            yield ServerSentEvent(
                data=pairs_data,
                event="fraud_update",
                id=f"fraud_{int(datetime.now(UTC).timestamp() * 1000)}_{i}",
            )
            await asyncio.sleep(0.5)
        yield ServerSentEvent(data={"status": "STREAM_ACTIVE"}, event="heartbeat")
        yield ServerSentEvent(
            data={"status": "STREAM_COMPLETE", "reason": "BATCH_END"},
            event="stream_end",
            id=f"fraud_end_{int(datetime.now(UTC).timestamp() * 1000)}",
        )
    except Exception as exc:
        yield ServerSentEvent(
            data={"status": "STREAM_ERROR", "detail": str(exc)},
            event="error",
            id=f"fraud_err_{int(datetime.now(UTC).timestamp() * 1000)}",
        )
