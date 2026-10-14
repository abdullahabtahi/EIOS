"""Warm start must read what the exporter writes, from one agreed root (R3, ADR-012).

The exporter writes `<root>/lakehouse/<product>/date=.../*.parquet`; the foundry writes
`<root>/raw/<product>/*.parquet`. The loader used to read only the second, and the router gave both
components `data/raw` as their root, so exported batches were never rehydrated after a restart.
"""

from pathlib import Path

import duckdb
import pytest

from eios.contracts.base import DataProductEnum
from eios.ingestion.config import IngestionConfig
from eios.ingestion.exporter import ParquetLakehouseExporter
from eios.ingestion.hot_state import HotStateEngine
from eios.ingestion.router import create_ingestion_app
from eios.ingestion.warm_start import ParquetWarmStartLoader

PRODUCT = DataProductEnum.TRADING_ACTIVITY


def _trade(trade_id: str) -> dict[str, object]:
    return {
        "trade_id": trade_id,
        "client_id": "cli_1",
        "symbol": "VOL_75",
        "side": "BUY",
        "volume": 1.5,
        "open_price": 100.0,
        "open_ts": "2026-10-13T10:00:00",
    }


def _write_foundry_baseline(root: Path, count: int) -> None:
    directory = root / "raw" / PRODUCT.value
    directory.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
            SELECT 'base_' || range::VARCHAR AS trade_id, 'cli_0' AS client_id, 'VOL_75' AS symbol,
                   'BUY' AS side, 1.0 AS volume, 100.0 AS open_price, now() AS open_ts
            FROM range({count})
        ) TO '{directory / "baseline.parquet"}' (FORMAT PARQUET)
        """  # noqa: S608
    )
    con.close()


def _count(engine: HotStateEngine) -> int:
    return engine.get_cursor().execute(f"SELECT count(*) FROM {PRODUCT.value}").fetchone()[0]  # noqa: S608


def test_exported_batches_are_rehydrated_by_the_loader(tmp_path: Path) -> None:
    ParquetLakehouseExporter(export_base_dir=tmp_path).export_batch(
        PRODUCT, [_trade("t1"), _trade("t2"), _trade("t3")]
    )
    engine = HotStateEngine()
    summary = ParquetWarmStartLoader(engine=engine, base_dir=tmp_path).load_all()
    assert summary.total_rows_loaded == 3
    assert PRODUCT.value in summary.products_loaded
    assert _count(engine) == 3


def test_foundry_baseline_still_loads_when_nothing_was_exported(tmp_path: Path) -> None:
    _write_foundry_baseline(tmp_path, count=5)
    engine = HotStateEngine()
    ParquetWarmStartLoader(engine=engine, base_dir=tmp_path).load_all()
    assert _count(engine) == 5


def test_an_exported_snapshot_supersedes_the_baseline_instead_of_doubling_it(
    tmp_path: Path,
) -> None:
    _write_foundry_baseline(tmp_path, count=5)
    ParquetLakehouseExporter(export_base_dir=tmp_path).export_batch(
        PRODUCT, [_trade("t1"), _trade("t2")]
    )
    engine = HotStateEngine()
    ParquetWarmStartLoader(engine=engine, base_dir=tmp_path).load_all()
    assert _count(engine) == 2


def test_default_root_is_the_data_directory_not_its_raw_subfolder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EIOS_LAKEHOUSE_ROOT", raising=False)
    assert IngestionConfig().parquet_lakehouse_root == "data"


def test_router_gives_the_exporter_and_the_loader_the_same_root(tmp_path: Path) -> None:
    app = create_ingestion_app(config=IngestionConfig(parquet_lakehouse_root=str(tmp_path)))
    assert app.state.exporter.base_dir == Path(app.state.config.warm_start_data_path)
    assert Path(app.state.config.warm_start_data_path) == tmp_path
