"""Tests for deterministic Parquet partition writing."""

from pathlib import Path
import pytest
from eios.foundry.storage.parquet_writer import write_deterministic_parquet


def test_write_deterministic_parquet_byte_identity(tmp_path: Path) -> None:
    data = [
        {"account_id": "CR2", "volume": 50.0, "status": "ACTIVE"},
        {"account_id": "CR1", "volume": 100.0, "status": "ACTIVE"},
        {"account_id": "CR3", "volume": 25.5, "status": "PENDING"},
    ]

    out_file1 = tmp_path / "run1" / "test.parquet"
    out_file2 = tmp_path / "run2" / "test.parquet"

    write_deterministic_parquet(data, out_file1, sort_key="account_id")
    write_deterministic_parquet(data, out_file2, sort_key="account_id")

    bytes1 = out_file1.read_bytes()
    bytes2 = out_file2.read_bytes()

    assert bytes1 == bytes2
