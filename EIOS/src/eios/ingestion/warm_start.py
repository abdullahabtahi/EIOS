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

    def _snapshot_glob(self, product: DataProductEnum) -> str | None:
        """Parquet files to rehydrate a product from, or None.

        Exported batches (`lakehouse/<product>/date=*/`) are the durable snapshot of what this platform
        ingested, so they win. The foundry baseline (`raw/<product>/`) seeds a product only when nothing was
        exported yet; loading both would count the same events twice.
        """
        exported = self.base_dir / "lakehouse" / product.value
        if any(exported.glob("date=*/*.parquet")):
            return str(exported / "date=*" / "*.parquet")
        baseline = self.base_dir / "raw" / product.value
        if any(baseline.glob("*.parquet")):
            return str(baseline / "*.parquet")
        return None

    def load_all(self) -> WarmStartSummary:
        """Rehydrate every product that has a Parquet snapshot or foundry baseline under base_dir."""
        start_time = time.perf_counter()
        total_rows = 0
        products_loaded = []

        cursor = self.engine.get_cursor()

        for product in DataProductEnum:
            glob_pattern = self._snapshot_glob(product)
            if glob_pattern is None:
                continue
            try:
                # Vectorized read with column-name alignment; the `date=` folder is a layout detail, not a column
                cursor.execute(
                    f"INSERT INTO {product.value} BY NAME SELECT * FROM read_parquet(?, hive_partitioning = false)",  # noqa: S608
                    [glob_pattern],
                )
                count = cursor.execute(f"SELECT count(*) FROM {product.value}").fetchone()[0]  # noqa: S608
                total_rows += count
                products_loaded.append(product.value)
                logger.info(f"Loaded {count} rows for {product.value} from {glob_pattern}.")
            except Exception as e:
                logger.warning(f"Failed to load Parquet files for {product.value}: {e}")

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return WarmStartSummary(
            total_rows_loaded=total_rows,
            load_duration_ms=duration_ms,
            products_loaded=products_loaded,
        )
