"""Replay a recent window of the AML world's transactions through the real ingestion pipeline (spec 035).

Every event goes through contract validation, the DLQ, the circuit breaker, the DQ monitor, the token vault and hot
state, exactly as a pushed event would. A small share of the replayed events is deliberately broken first (the
foundry's `BreachInjector`), so enforcement is measured against a known truth: every planted breach must be quarantined
and every healthy event accepted. Only the evaluation reads which events were planted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from eios.contracts.base import DataProductEnum, DataProductEvent, TenantEnum
from eios.foundry.noise.breach_injector import BreachInjector
from eios.foundry.rng import RNGManager
from eios.foundry.scenarios.aml_world import AmlWorld
from eios.ingestion.config import IngestionConfig
from eios.ingestion.dlq import ContractBreachRecord
from eios.ingestion.processor import IngestionPipeline
from eios.ingestion.queue import IngestionQueue

REPLAY_HOURS = 168  # [ASSUMPTION] a week: enough events for a stable breach rate, few enough to replay at start
BREACH_SHARE = 0.004  # [ASSUMPTION] about eight times the circuit breaker's budget, so the board has a real incident
PRODUCT = DataProductEnum.TRANSACTIONS_AML
TENANT = TenantEnum.DERIV_MFSA
_SEED_SALT = 0x0B5  # keeps the breach stream independent of the world's other streams


@dataclass(frozen=True)
class ReplayOutcome:
    pipeline: IngestionPipeline
    window_start: datetime
    window_end: datetime
    offered: int
    accepted: int
    rejected: int
    planted: int
    caught: int  # planted breaches that were quarantined
    false_rejects: int  # healthy events that were quarantined
    breach_rate: float
    dlq: tuple[ContractBreachRecord, ...]
    accepted_events: tuple[DataProductEvent, ...]

    @property
    def enforcement_correct(self) -> bool:
        return self.caught == self.planted and self.false_rejects == 0


def _payload(row: Any) -> dict[str, Any]:
    return {
        "txn_id": row.txn_id,
        "client_id": row.client_id,
        "txn_type": row.transaction_type,
        "amount": float(row.amount),
        "currency": row.currency,
        "payment_method_id": row.payment_token,
        "timestamp": row.timestamp.to_pydatetime(),
        "status": row.status,
    }


def replay_transactions(world: AmlWorld, as_of: datetime) -> ReplayOutcome:
    tx = world.transactions
    window = tx[
        (tx["timestamp"] <= as_of) & (tx["timestamp"] > as_of - timedelta(hours=REPLAY_HOURS))
    ]
    rows = [(_payload(r), r.timestamp.to_pydatetime()) for r in window.itertuples()]
    rng = np.random.default_rng(world.config.seed ^ _SEED_SALT)
    planted_at = set(
        rng.choice(len(rows), size=round(len(rows) * BREACH_SHARE), replace=False).tolist()
    )
    injector = BreachInjector(RNGManager(world.config.seed ^ _SEED_SALT))
    pipeline = IngestionPipeline(
        config=IngestionConfig(),
        queue=IngestionQueue(maxsize=len(rows) + 1),
    )
    planted_ids: set[str] = set()
    rejected_ids: set[str] = set()
    accepted: list[DataProductEvent] = []
    for i, (payload, ts) in enumerate(rows):
        if i in planted_at:
            planted_ids.add(payload["txn_id"])
            payload = injector.inject_transaction_breaches([payload], "NEGATIVE_AMOUNT")[0]
        event = DataProductEvent(
            product_name=PRODUCT, tenant_id=TENANT, event_timestamp=ts, payload=payload
        )
        result = pipeline.process_event(event)
        if result.is_accepted:
            accepted.append(event)
        else:
            rejected_ids.add(str(payload["txn_id"]))
    dlq = tuple(pipeline.dlq_dispatcher.flush())
    return ReplayOutcome(
        pipeline=pipeline,
        window_start=as_of - timedelta(hours=REPLAY_HOURS),
        window_end=as_of,
        offered=len(rows),
        accepted=len(accepted),
        rejected=len(rejected_ids),
        planted=len(planted_ids),
        caught=len(planted_ids & rejected_ids),
        false_rejects=len(rejected_ids - planted_ids),
        breach_rate=len(rejected_ids) / len(rows) if rows else 0.0,
        dlq=dlq,
        accepted_events=tuple(accepted),
    )
