"""Deterministic sorted Parquet partition writer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def write_deterministic_parquet(
    records: list[dict[str, Any]],
    out_path: Path | str,
    sort_key: str | None = None,
) -> None:
    """Writes records to a Parquet file with deterministic column ordering and compression."""
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        table = pa.Table.from_pylist([])
        pq.write_table(table, out_file)
        return

    # Deterministically order columns alphabetically
    all_keys = sorted({k for r in records for k in r.keys()})
    sorted_records = []
    for r in records:
        sorted_records.append({k: r.get(k) for k in all_keys})

    # Sort rows by sort_key if provided
    if sort_key and sort_key in all_keys:
        sorted_records.sort(key=lambda x: str(x.get(sort_key, "")))

    table = pa.Table.from_pylist(sorted_records)

    pq.write_table(
        table,
        out_file,
        compression="snappy",
        use_dictionary=True,
        row_group_size=64_000,
    )


class DeterministicParquetWriter:
    """Deterministic Parquet writer for batch datasets."""

    @staticmethod
    def write_partition(
        records: Any,
        out_path: Path | str,
        sort_columns: list[str] | None = None,
    ) -> Path:
        out_file = Path(out_path)
        if hasattr(records, "to_dicts"):
            # Polars DataFrame
            record_dicts = records.to_dicts()
        elif isinstance(records, list):
            record_dicts = records
        else:
            record_dicts = list(records)

        sort_key = sort_columns[0] if sort_columns else None
        write_deterministic_parquet(record_dicts, out_file, sort_key=sort_key)
        return out_file
