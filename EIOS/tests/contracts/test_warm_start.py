"""Tests for Parquet Warm-Start Cold-Boot Engine and /readyz probe (US3)."""

import time
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from eios.ingestion.hot_state import HotStateEngine
from eios.ingestion.router import create_ingestion_app
from eios.ingestion.warm_start import ParquetWarmStartLoader


@pytest.fixture
def synthetic_parquet_dir(tmp_path: Path) -> Path:
    """Generate 100,000 synthetic trading events in a temporary Parquet file."""
    data_dir = tmp_path / "raw" / "trading_activity"
    data_dir.mkdir(parents=True, exist_ok=True)
    file_path = data_dir / "snapshot_001.parquet"

    con = duckdb.connect()
    con.execute(f"""
        COPY (
            SELECT 
                'trd_' || range::VARCHAR AS trade_id,
                'cli_' || (range % 1000)::VARCHAR AS client_id,
                'VOL_75' AS symbol,
                'BUY' AS side,
                1.5 AS volume,
                100.0 + (range % 50) AS open_price,
                now() - INTERVAL (range % 3600) SECOND AS open_ts
            FROM range(100000)
        ) TO '{file_path}' (FORMAT PARQUET)
    """)
    con.close()
    return tmp_path


def test_warm_start_loads_100k_records_under_3_seconds(synthetic_parquet_dir: Path):
    """ADR-012 benchmark: cold boot must rehydrate 100,000 rows in < 3.0s."""
    engine = HotStateEngine()
    loader = ParquetWarmStartLoader(engine=engine, base_dir=synthetic_parquet_dir)

    start = time.perf_counter()
    summary = loader.load_all()
    duration = time.perf_counter() - start

    assert duration < 3.0  # ADR-012 target
    assert summary.total_rows_loaded >= 100000
    assert summary.load_duration_ms < 3000.0

    # Verify DuckDB has the records
    cursor = engine.get_cursor()
    count = cursor.execute("SELECT count(*) FROM trading_activity").fetchone()[0]
    assert count >= 100000


def test_readyz_probe_lifecycle(synthetic_parquet_dir: Path):
    """Test /readyz returns 503 before warm-start and 200 after warm-start."""
    engine = HotStateEngine()
    app = create_ingestion_app()
    # Explicitly set app ready state to False
    app.state.is_ready = False

    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json()["status"] == "INITIALIZING"

    # Simulate warm start completed
    loader = ParquetWarmStartLoader(engine=engine, base_dir=synthetic_parquet_dir)
    res = loader.load_all()
    app.state.is_ready = True
    app.state.warm_start_duration_ms = res.load_duration_ms

    resp_after = client.get("/readyz")
    assert resp_after.status_code == 200
    assert resp_after.json()["status"] == "READY"
    assert resp_after.json()["warm_start_duration_ms"] > 0
