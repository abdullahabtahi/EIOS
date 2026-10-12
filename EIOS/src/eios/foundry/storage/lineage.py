"""Foundry Multimodal Data Plane (MMDP) dataset transaction and lineage metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def write_dataset_lineage(
    dataset_dir: Path | str,
    dataset_id: str,
    schema_model: str,
    upstream_inputs: List[str],
    record_count: int,
    manifest_id_ref: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Emits _lineage.json into the dataset directory capturing Foundry MMDP transaction lineage."""
    target_dir = Path(dataset_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    lineage_file = target_dir / "_lineage.json"

    payload: Dict[str, Any] = {
        "dataset_id": dataset_id,
        "transaction_type": "SNAPSHOT",
        "schema_model": schema_model,
        "upstream_inputs": upstream_inputs,
        "record_count": record_count,
        "manifest_id_ref": manifest_id_ref,
        "metadata": metadata or {},
    }

    lineage_file.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return lineage_file
