"""Tests for Parquet Lakehouse Exporter and _lineage.json manifest (US6)."""

import json
from pathlib import Path

from eios.contracts.base import DataProductEnum
from eios.ingestion.exporter import ParquetLakehouseExporter


def test_exporter_writes_parquet_and_lineage_manifest(tmp_path: Path):
    exporter = ParquetLakehouseExporter(export_base_dir=tmp_path)
    product = DataProductEnum.TRADING_ACTIVITY

    records = [
        {
            "trade_id": f"trd_exp_{i}",
            "client_id": "cli_99",
            "symbol": "VOL_75",
            "side": "BUY",
            "volume": 1.0,
            "open_price": 500.0,
            "open_ts": "2026-10-04T12:00:00Z",
        }
        for i in range(25)
    ]

    export_res = exporter.export_batch(product, records)
    assert export_res.record_count == 25
    assert export_res.parquet_file.exists()
    assert export_res.lineage_file.exists()

    # Verify _lineage.json contents
    with open(export_res.lineage_file, encoding="utf-8") as f:
        lineage = json.load(f)

    assert lineage["product_name"] == "trading_activity"
    assert lineage["record_count"] == 25
    assert "data_hash_sha256" in lineage
    assert "export_timestamp" in lineage
    assert len(lineage["data_hash_sha256"]) == 64
