"""Tests for Foundry manifest loading, validation, and Merkle root hashing."""

import json
from pathlib import Path
import pytest
from eios.foundry.manifest import (
    FoundryManifest,
    compute_dataset_merkle_hash,
    validate_manifest_dict,
)


@pytest.fixture
def valid_manifest_data() -> dict[str, object]:
    return {
        "manifest_id": "123e4567-e89b-12d3-a456-426614174000",
        "manifest_version": "1.0.0",
        "seed": 42,
        "seed_tier": "dev",
        "git_sha": "a" * 40,
        "spec_hash": "b" * 64,
        "generator_versions": {
            "gen_client": "1.0.0",
            "gen_aml": "1.0.0",
            "gen_partner": "1.0.0",
            "gen_financial": "1.0.0",
            "gen_competitive": "1.0.0",
            "gen_operational": "1.0.0",
            "gen_causal_truth": "1.0.0",
        },
        "dataset_hash": "c" * 64,
        "generated_at": "2026-10-02T12:00:00Z",
    }


def test_manifest_validation_success(valid_manifest_data: dict[str, object]) -> None:
    manifest = validate_manifest_dict(valid_manifest_data)
    assert manifest.seed == 42
    assert manifest.seed_tier == "dev"


def test_manifest_validation_invalid_tier(valid_manifest_data: dict[str, object]) -> None:
    data = dict(valid_manifest_data)
    data["seed_tier"] = "invalid_tier"
    with pytest.raises(ValueError, match="seed_tier"):
        validate_manifest_dict(data)


def test_compute_dataset_merkle_hash(tmp_path: Path) -> None:
    file_a = tmp_path / "part_a.parquet"
    file_b = tmp_path / "part_b.parquet"
    file_a.write_bytes(b"content_a")
    file_b.write_bytes(b"content_b")

    hash1 = compute_dataset_merkle_hash(tmp_path)
    hash2 = compute_dataset_merkle_hash(tmp_path)

    assert hash1 == hash2
    assert len(hash1) == 64
