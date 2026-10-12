"""Tests for In-Memory DuckDB Hot-State Engine and concurrency (US3)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import time
import pytest

from eios.contracts.base import DataProductEnum
from eios.ingestion.hot_state import HotStateEngine


def test_hot_state_engine_initializes_all_14_tables():
    engine = HotStateEngine()
    tables = engine.list_tables()
    assert len(tables) >= 14
    for product in DataProductEnum:
        assert product.value in tables


def test_concurrent_readers_and_writers():
    engine = HotStateEngine()
    
    def writer_task(worker_id: int):
        for i in range(50):
            engine.insert_event(
                DataProductEnum.TRADING_ACTIVITY,
                {
                    "trade_id": f"trd_w{worker_id}_{i}",
                    "client_id": f"cli_{worker_id}",
                    "symbol": "VOL_75",
                    "side": "BUY",
                    "volume": 1.0,
                    "open_price": 500.0,
                    "open_ts": datetime.now(timezone.utc).isoformat(),
                },
            )

    def reader_task():
        latencies = []
        for _ in range(50):
            start = time.perf_counter()
            cursor = engine.get_cursor()
            res = cursor.execute("SELECT count(*), avg(open_price) FROM trading_activity").fetchall()
            latencies.append((time.perf_counter() - start) * 1000.0)
            assert res is not None
        return latencies

    with ThreadPoolExecutor(max_workers=6) as executor:
        writer_futures = [executor.submit(writer_task, wid) for wid in range(3)]
        reader_futures = [executor.submit(reader_task) for _ in range(3)]

        for f in writer_futures:
            f.result()
        all_latencies = []
        for f in reader_futures:
            all_latencies.extend(f.result())

    # p95 query latency under 15ms
    all_latencies.sort()
    p95_idx = int(len(all_latencies) * 0.95)
    p95_latency = all_latencies[p95_idx]
    assert p95_latency < 15.0


def test_sliding_window_eviction():
    engine = HotStateEngine()
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(hours=48)).isoformat()
    recent_ts = (now - timedelta(hours=2)).isoformat()

    engine.insert_event(
        DataProductEnum.TRADING_ACTIVITY,
        {
            "trade_id": "trd_old_01",
            "client_id": "cli_01",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": 1.0,
            "open_price": 500.0,
            "open_ts": old_ts,
        },
    )
    engine.insert_event(
        DataProductEnum.TRADING_ACTIVITY,
        {
            "trade_id": "trd_new_01",
            "client_id": "cli_01",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": 1.0,
            "open_price": 500.0,
            "open_ts": recent_ts,
        },
    )

    count_before = engine.get_cursor().execute("SELECT count(*) FROM trading_activity").fetchone()[0]
    assert count_before == 2

    # Evict records older than 24h
    evicted = engine.evict_older_than(DataProductEnum.TRADING_ACTIVITY, "open_ts", hours=24)
    assert evicted == 1

    count_after = engine.get_cursor().execute("SELECT count(*) FROM trading_activity").fetchone()[0]
    assert count_after == 1
