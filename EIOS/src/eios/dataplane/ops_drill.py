"""A real restore drill: export what the pipeline accepted, rehydrate a fresh hot state from it, compare (spec 035).

This is the warm-start path of runbook 8 run for real: the accepted events are exported to Parquet with lineage
manifests, a new `HotStateEngine` is rehydrated by `ParquetWarmStartLoader`, and the restored rows and a column total are
compared with what was exported. The checkpoint hash is the SHA-256 over the lineage hashes of the exported batches.
It proves the warm-start path only; key rotation and a regional failover are not exercised here.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eios.contracts.base import DataProductEnum, DataProductEvent
from eios.ingestion.exporter import ParquetLakehouseExporter
from eios.ingestion.hot_state import HotStateEngine
from eios.ingestion.warm_start import ParquetWarmStartLoader

TOTAL_TOLERANCE = 0.01  # USD: a column total is float arithmetic, not a count


@dataclass(frozen=True)
class DrillResult:
    products: tuple[str, ...]
    rows_exported: int
    rows_restored: int
    total_exported: float
    total_restored: float
    export_ms: float
    restore_ms: float
    checkpoint_hash: str
    ran_at: datetime

    @property
    def verified(self) -> bool:
        return (
            self.rows_exported == self.rows_restored > 0
            and abs(self.total_exported - self.total_restored) <= TOTAL_TOLERANCE
        )


def _by_product(events: Sequence[DataProductEvent]) -> dict[DataProductEnum, list[dict[str, Any]]]:
    grouped: dict[DataProductEnum, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        grouped[e.product_name].append(e.payload)
    return grouped


def run_restore_drill(events: Sequence[DataProductEvent]) -> DrillResult:
    grouped = _by_product(events)
    with tempfile.TemporaryDirectory(prefix="eios-drill-") as tmp:
        root = Path(tmp)
        started = time.perf_counter()
        exporter = ParquetLakehouseExporter(root)
        hashes: list[str] = []
        for product, records in sorted(grouped.items(), key=lambda kv: kv[0].value):
            result = exporter.export_batch(product, records)
            hashes.append(json.loads(result.lineage_file.read_text())["data_hash_sha256"])
        export_ms = (time.perf_counter() - started) * 1000.0

        engine = HotStateEngine()
        summary = ParquetWarmStartLoader(engine, root).load_all()
        cur = engine.get_cursor()
        restored_total = sum(
            float(cur.execute(f"SELECT coalesce(sum(amount), 0) FROM {p.value}").fetchone()[0])  # noqa: S608
            for p in grouped
            if p is DataProductEnum.TRANSACTIONS_AML
        )
        engine.close()
    return DrillResult(
        products=tuple(sorted(p.value for p in grouped)),
        rows_exported=sum(len(r) for r in grouped.values()),
        rows_restored=summary.total_rows_loaded,
        total_exported=sum(
            float(r["amount"]) for r in grouped.get(DataProductEnum.TRANSACTIONS_AML, [])
        ),
        total_restored=restored_total,
        export_ms=round(export_ms, 1),
        restore_ms=round(summary.load_duration_ms, 1),
        checkpoint_hash=hashlib.sha256("".join(hashes).encode()).hexdigest(),
        ran_at=datetime.now(UTC),
    )
