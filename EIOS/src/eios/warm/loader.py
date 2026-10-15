"""Run a world's history through the real ingestion pipeline and into the warm tier.

The same replay that measures contract enforcement on the operations board (`dataplane.ops_replay`) supplies the
accepted events and the quarantined breaches; here they go to a sink instead of being counted. The batch id is derived
from the world and the window, so loading the same history twice is a no-op, not a duplicate.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from eios.dataplane.ops_replay import PRODUCT, replay_transactions
from eios.foundry.scenarios.aml_world import AmlWorld
from eios.warm.rows import breach_rows, event_rows
from eios.warm.sink import WarmSink

SOURCE = "foundry:aml-world"  # [ILLUSTRATIVE] synthetic data; the label travels with every row


@dataclass(frozen=True)
class LoadSummary:
    batch_id: str
    offered: int
    loaded: int
    quarantined: int
    window_start: datetime
    window_end: datetime


def batch_id_for(world: AmlWorld, hours: int, plant_breaches: float = 0.0) -> str:
    digest = hashlib.sha256(
        f"{world.config.fingerprint()}|{hours}|{plant_breaches}".encode()
    ).hexdigest()
    return f"batch_{digest[:12]}"


def load_transactions_history(
    world: AmlWorld,
    as_of: datetime | None,
    sink: WarmSink,
    *,
    hours: int | None = None,
    now: datetime | None = None,
    plant_breaches: float = 0.0,
) -> LoadSummary:
    """`plant_breaches` is the share of events to break on purpose, to show quarantine at work. A history load plants none:
    the board's enforcement measurement does that on its own replay, and the history must stay exact."""
    # Everything the world holds: a few story events are stamped just after the world's as-of, and the engine counts them.
    stamps = world.transactions["timestamp"]
    end = as_of or (stamps.max().to_pydatetime() + timedelta(seconds=1))
    # Unless told otherwise, the window is the world's whole span, to the hour, not a fixed number of hours back.
    hours = hours or math.ceil((end - stamps.min().to_pydatetime()).total_seconds() / 3600) + 1
    outcome = replay_transactions(world, end, hours, breach_share=plant_breaches)
    batch = batch_id_for(world, hours, plant_breaches)
    stamp = now or datetime.now(UTC)
    loaded = sink.load(
        PRODUCT,
        event_rows(outcome.accepted_events, batch_id=batch, source=SOURCE, loaded_at=stamp),
        batch_id=batch,
    )
    quarantined = sink.quarantine(
        breach_rows(outcome.dlq, batch_id=batch, source=SOURCE, loaded_at=stamp), batch_id=batch
    )
    return LoadSummary(
        batch, outcome.offered, loaded, quarantined, outcome.window_start, outcome.window_end
    )
