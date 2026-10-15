"""Parity: the warehouse and the engine's own hot-path totals must tell the same story, judged on the whole world.

The engine computes each account's deposit and withdrawal volume straight from the transaction frame. The warm tier
gets the same events through contract validation and a load, and answers through a named query. Any difference would
mean the pipeline, the date bucketing or the query lost or invented money; the only legitimate difference is an event
that was quarantined, and then it equals that event's amount exactly.
"""

from datetime import timedelta

import pytest

from eios.dataplane.aml_engine import AmlSnapshot
from eios.warm.loader import load_transactions_history
from eios.warm.sink import LocalWarmSink
from eios.warm.store import LocalWarmStore

ACCOUNTS = 80  # the busiest accounts on each side: where a lost event would show most


def _warm_totals(store: LocalWarmStore, snapshot: AmlSnapshot, client: str) -> tuple[float, float]:
    as_of = (
        snapshot.world.config.as_of
    )  # the tool's window: 30 days back, a day of allowance past the as-of
    rows = store.run(
        "account_daily_activity",
        {
            "client_id": client,
            "start": (as_of - timedelta(days=30)).isoformat(),
            "end": (as_of + timedelta(days=1)).isoformat(),
        },
    ).rows
    return sum(r["deposits"] for r in rows), sum(r["withdrawals"] for r in rows)


@pytest.fixture(scope="module")
def warm(aml_snapshot: AmlSnapshot) -> LocalWarmStore:
    sink = LocalWarmSink()
    world = aml_snapshot.world
    summary = load_transactions_history(world, None, sink)
    assert summary.quarantined == 0 and summary.loaded == summary.offered
    return LocalWarmStore(sink.connection)


def test_every_busy_account_has_the_same_volumes_hot_and_warm(
    aml_snapshot: AmlSnapshot, warm: LocalWarmStore
) -> None:
    facts = aml_snapshot.facts
    busy = {
        *facts.nlargest(ACCOUNTS, "dep_volume").index,
        *facts.nlargest(ACCOUNTS, "wd_volume").index,
    }
    off = []
    for client in sorted(busy):
        dep, wd = _warm_totals(warm, aml_snapshot, str(client))
        if (
            abs(dep - facts.loc[client, "dep_volume"]) > 0.01
            or abs(wd - facts.loc[client, "wd_volume"]) > 0.01
        ):
            off.append(
                (client, dep, facts.loc[client, "dep_volume"], wd, facts.loc[client, "wd_volume"])
            )
    assert not off, f"{len(off)} of {len(busy)} accounts disagree: {off[:3]}"


def test_a_quarantined_event_is_the_only_thing_that_can_make_them_differ(
    aml_snapshot: AmlSnapshot,
) -> None:
    world = aml_snapshot.world
    sink = LocalWarmSink()
    summary = load_transactions_history(world, None, sink, plant_breaches=0.004)
    assert summary.quarantined > 0
    store = LocalWarmStore(sink.connection)
    have = {
        r[0]
        for r in sink.connection.execute("SELECT txn_id FROM warm_aml.transactions_aml").fetchall()
    }
    tx = world.transactions
    lost = tx[~tx.txn_id.isin(have)]
    deposits_lost = lost[(lost.transaction_type == "DEPOSIT") & (lost.status == "COMPLETED")]
    facts = aml_snapshot.facts
    for client, amount in deposits_lost.groupby("client_id").amount.sum().head(10).items():
        dep, _ = _warm_totals(store, aml_snapshot, str(client))
        assert facts.loc[client, "dep_volume"] - dep == pytest.approx(amount, abs=0.01)
