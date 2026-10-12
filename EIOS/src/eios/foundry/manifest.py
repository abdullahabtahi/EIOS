"""Foundry manifest loading, validation, and Merkle root calculation."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Dict, Literal
from pydantic import BaseModel, Field, field_validator


class FoundryManifest(BaseModel):
    """Pydantic model representing the Foundry Run Manifest."""

    manifest_id: str
    manifest_version: str = "1.0.0"
    seed: int
    seed_tier: Literal["dev", "validation", "sealed"]
    git_sha: str = Field(min_length=40, max_length=40)
    spec_hash: str = Field(min_length=64, max_length=64)
    generator_versions: Dict[str, str]
    dataset_hash: str = Field(min_length=64, max_length=64)
    generated_at: str

    @field_validator("seed_tier")
    @classmethod
    def validate_sealed_environment(cls, v: str) -> str:
        if v == "sealed" and not os.environ.get("CI_RELEASE_CANDIDATE"):
            raise PermissionError(
                "Sealed datasets can only be generated in CI release-candidate runs."
            )
        return v


def validate_manifest_dict(data: dict[str, object]) -> FoundryManifest:
    """Validates raw dictionary data against the FoundryManifest model."""
    return FoundryManifest.model_validate(data)


def compute_dataset_merkle_hash(dataset_dir: Path | str) -> str:
    """Computes a deterministic SHA-256 Merkle root of all files in dataset_dir."""
    path = Path(dataset_dir)
    if not path.exists():
        return hashlib.sha256(b"").hexdigest()

    file_hashes: list[str] = []
    # Collect all regular files, sorted deterministically by relative path
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and not file_path.name.startswith("."):
            content = file_path.read_bytes()
            file_hashes.append(hashlib.sha256(content).hexdigest())

    if not file_hashes:
        return hashlib.sha256(b"").hexdigest()

    # Combine file hashes deterministically
    combined = "".join(file_hashes).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()
