"""Parquet Lakehouse micro-batch exporter with immutable _lineage.json manifests (US6)."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from uuid import uuid4
import duckdb

from eios.contracts.base import DataProductEnum


@dataclass
class ExportResult:
    """Artifact references from an export run."""
    parquet_file: Path
    lineage_file: Path
    record_count: int


class ParquetLakehouseExporter:
    """Exports micro-batches of hot state records to partitioned Parquet files with lineage."""

    def __init__(self, export_base_dir: Path | str = "data") -> None:
        self.base_dir = Path(export_base_dir)

    def export_batch(
        self,
        product: DataProductEnum,
        records: list[dict[str, Any]],
        git_commit_sha: str = "eios-v1.0.0-dev",
    ) -> ExportResult:
        """Serialize records to partitioned Parquet and attach immutable _lineage.json."""
        if not records:
            raise ValueError("Cannot export empty batch of records")

        product_name = product.value if isinstance(product, DataProductEnum) else str(product)
        batch_id = f"batch_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        # Partitioned lakehouse directory
        target_dir = self.base_dir / "lakehouse" / product_name / f"date={date_str}"
        target_dir.mkdir(parents=True, exist_ok=True)

        parquet_path = target_dir / f"{batch_id}.parquet"
        lineage_path = target_dir / f"{batch_id}_lineage.json"

        # Compute deterministic SHA256 of raw records
        serialized_data = json.dumps(records, sort_keys=True, default=str).encode("utf-8")
        data_hash = hashlib.sha256(serialized_data).hexdigest()

        # Write Parquet via DuckDB read_json_auto
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ndjson", delete=False) as ndjson_file:
            for r in records:
                ndjson_file.write(json.dumps(r, default=str) + "\n")
            ndjson_path = ndjson_file.name

        try:
            con = duckdb.connect()
            con.execute("CREATE TABLE tmp_export AS SELECT * FROM read_json_auto(?)", [ndjson_path])
            con.execute(f"COPY tmp_export TO '{parquet_path}' (FORMAT PARQUET)")
            con.close()
        finally:
            if os.path.exists(ndjson_path):
                os.remove(ndjson_path)

        # Build lineage manifest
        lineage_manifest = {
            "batch_id": batch_id,
            "product_name": product_name,
            "record_count": len(records),
            "export_timestamp": now.isoformat(),
            "data_hash_sha256": data_hash,
            "git_commit_sha": git_commit_sha,
            "parquet_file": str(parquet_path.name),
            "source_topics": [f"eios.l1.{product_name}.v1"],
        }

        with open(lineage_path, "w", encoding="utf-8") as f:
            json.dump(lineage_manifest, f, indent=2)

        # Also write the canonical _lineage.json in the partition folder
        canonical_lineage = target_dir / "_lineage.json"
        with open(canonical_lineage, "w", encoding="utf-8") as f:
            json.dump(lineage_manifest, f, indent=2)

        return ExportResult(
            parquet_file=parquet_path,
            lineage_file=lineage_path,
            record_count=len(records),
        )
