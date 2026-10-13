"""Parquet Warm-Start Loader for cold-boot in-memory hot-state rehydration (ADR-012)."""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from eios.contracts.base import DataProductEnum
from eios.ingestion.hot_state import HotStateEngine

logger = logging.getLogger("eios.ingestion.warm_start")


@dataclass
class WarmStartSummary:
    """Telemetry summary of warm-start cold-boot execution."""

    total_rows_loaded: int
    load_duration_ms: float
    products_loaded: list[str]


class ParquetWarmStartLoader:
    """Scans Parquet lakehouse partitions and executes vectorized DuckDB ingestion."""

    def __init__(self, engine: HotStateEngine, base_dir: Path | str = "data") -> None:
        self.engine = engine
        self.base_dir = Path(base_dir)

    def load_all(self) -> WarmStartSummary:
        """Scan all product subdirectories in base_dir/raw and load Parquet files."""
        start_time = time.perf_counter()
        total_rows = 0
        products_loaded = []
        raw_dir = self.base_dir / "raw"

        if not raw_dir.exists():
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return WarmStartSummary(0, duration_ms, [])

        cursor = self.engine.get_cursor()

        for product in DataProductEnum:
            prod_dir = raw_dir / product.value
            if not prod_dir.exists():
                continue

            parquet_files = list(prod_dir.glob("*.parquet"))
            if not parquet_files:
                continue

            glob_pattern = str(prod_dir / "*.parquet")
            try:
                # Vectorized DuckDB Parquet read with column name alignment
                cursor.execute(
                    f"INSERT INTO {product.value} BY NAME SELECT * FROM read_parquet(?)",
                    [glob_pattern],
                )
                count = cursor.execute(f"SELECT count(*) FROM {product.value}").fetchone()[0]
                total_rows += count
                products_loaded.append(product.value)
                logger.info(f"Loaded {count} rows for {product.value} from Parquet lakehouse.")
            except Exception as e:
                logger.warning(f"Failed to load Parquet files for {product.value}: {e}")

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return WarmStartSummary(
            total_rows_loaded=total_rows,
            load_duration_ms=duration_ms,
            products_loaded=products_loaded,
        )
