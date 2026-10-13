"""SCM Synthesis and Causal What-If Simulation API Routes (F019 Phase 2, T009)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel, Field

from eios.cockpit.executive import ExecutiveCockpitService

router = APIRouter(tags=["SCM Synthesis"])
exec_svc = ExecutiveCockpitService()

WHAT_IF_PATH = "/api/v1/synthesis/what-if"
BRIEFING_PATH = "/api/v1/synthesis/briefing"
DAG_PATH = "/api/v1/synthesis/dag"
STREAM_PATH = "/api/v1/synthesis/stream"


class WhatIfSimulationRequest(BaseModel):
    shock_param: str = Field(
        default="competitor_commission_bps", description="Causal parameter shock identifier"
    )
    magnitude_pct: float = Field(
        default=25.0, description="Percentage shock magnitude (-100% to +100%)"
    )


@router.post(WHAT_IF_PATH)
def simulate_what_if(req: WhatIfSimulationRequest) -> dict[str, Any]:
    """Executes DoWhy refuter-checked causal SCM shock simulation with exact 100% Hare-Niemeyer attribution."""
    result = exec_svc.simulate_what_if_shock(
        shock_param=req.shock_param,
        magnitude_pct=req.magnitude_pct,
    )
    # Validate Hare-Niemeyer 100% invariant
    attr_sum = result.get("attribution_sum_pct", 0.0)
    if not (99.98 <= attr_sum <= 100.02):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Causal Hare-Niemeyer attribution violation: sum is {attr_sum}%, expected 100.0%",
        )
    return result


@router.get(BRIEFING_PATH)
def get_morning_briefing() -> dict[str, Any]:
    """Returns 4-horizon executive morning briefing with DoWhy refuter statuses and verified citations."""
    briefing = exec_svc.get_morning_briefing()
    return briefing.to_contract_dict()


@router.get(DAG_PATH)
def get_causal_dag() -> dict[str, Any]:
    """Returns Structural Causal Model DAG nodes, edges, and DoWhy refuter certification states."""
    dag = exec_svc.get_causal_dag()
    return dag.to_contract_dict()


@router.get(STREAM_PATH, response_class=EventSourceResponse)
async def stream_synthesis_briefing() -> AsyncIterable[ServerSentEvent]:
    """Streams live executive briefing updates via native Server-Sent Events."""
    for i in range(3):
        briefing_data = get_morning_briefing()
        yield ServerSentEvent(
            data=briefing_data,
            event="briefing_update",
            id=f"briefing_{int(datetime.now(UTC).timestamp() * 1000)}_{i}",
        )
        await asyncio.sleep(0.5)
    yield ServerSentEvent(data={"status": "STREAM_ACTIVE"}, event="heartbeat")
