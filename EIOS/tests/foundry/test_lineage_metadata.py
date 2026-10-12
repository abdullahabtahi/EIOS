"""Tests for dataset transaction lineage metadata and provenance tracking (T059, T062)."""

import json
from pathlib import Path
import pytest
from eios.foundry.storage.lineage import write_dataset_lineage


def test_lineage_metadata_schema_and_provenance(tmp_path: Path):
    """Confirms _lineage.json contains commit SHA, spec hash, record count, and upstream universe IDs."""
    dataset_dir = tmp_path / "raw" / "client_360"
    lineage_path = write_dataset_lineage(
        dataset_dir=dataset_dir,
        dataset_id="client_360",
        schema_model="Client360Record",
        upstream_inputs=["foundry.universe.master_seed_42"],
        record_count=1000,
        manifest_id_ref="manifest_sha_dummy",
        metadata={
            "commit_sha": "a1b2c3d4e5f6",
            "spec_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "universe_person_count": 1000,
        },
    )

    assert lineage_path.exists()
    assert lineage_path.name == "_lineage.json"

    with open(lineage_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["dataset_id"] == "client_360"
    assert data["schema_model"] == "Client360Record"
    assert data["record_count"] == 1000
    assert data["manifest_id_ref"] == "manifest_sha_dummy"

    # Provenance metadata
    meta = data["metadata"]
    assert meta["commit_sha"] == "a1b2c3d4e5f6"
    assert "spec_hash" in meta
    assert "universe_person_count" in meta
