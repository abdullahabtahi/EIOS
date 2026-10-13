"""Shared pytest fixtures for Layer 1 Ingestion and Contract tests."""

import os
import shutil
import tempfile
from collections.abc import Generator
from datetime import UTC, datetime

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest


@pytest.fixture
def sample_salt() -> str:
    """Deterministic HMAC salt for testing."""
    return "test-salt-secret-9941a5b8e2d4c0"


@pytest.fixture
def in_memory_duckdb() -> Generator[duckdb.DuckDBPyConnection]:
    """Provide a fresh named in-memory DuckDB connection."""
    conn = duckdb.connect(":memory:eios_test_conftest")
    yield conn
    conn.close()


@pytest.fixture
def temp_parquet_dir() -> Generator[str]:
    """Create a temporary directory with test Parquet partitions."""
    temp_dir = tempfile.mkdtemp(prefix="eios_test_lakehouse_")

    # Create product directory for trading_activity
    trading_dir = os.path.join(temp_dir, "trading_activity")
    os.makedirs(trading_dir, exist_ok=True)

    # Write a small sample parquet partition (100 rows)
    data = {
        "trade_id": [f"TRD_{i:06d}" for i in range(100)],
        "client_id": [f"CR_{i % 10:04d}" for i in range(100)],
        "symbol": ["BOOM_1000" if i % 2 == 0 else "VOL_75" for i in range(100)],
        "side": ["BUY" if i % 2 == 0 else "SELL" for i in range(100)],
        "volume": [float(1 + (i % 5)) for i in range(100)],
        "open_price": [1000.0 + float(i) for i in range(100)],
        "open_ts": [datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)] * 100,
    }
    table = pa.Table.from_pydict(data)
    pq.write_table(table, os.path.join(trading_dir, "batch_001.parquet"))

    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)
