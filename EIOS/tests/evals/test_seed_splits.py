"""Tests for Multi-Seed Split Runner & Seed Manifests (T040)."""

from eios.evals.models import Tier
from evals.suites.splits.runner import (
    TIER_SEEDS,
    generate_seed_manifest,
    run_seed_splits,
)


def test_tier_seed_allocations():
    assert len(TIER_SEEDS[Tier.DEV]) == 1
    assert TIER_SEEDS[Tier.DEV] == [42]

    # Validation must have >= 10 seeds
    assert len(TIER_SEEDS[Tier.VALIDATION]) >= 10
    assert TIER_SEEDS[Tier.VALIDATION] == [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]

    # Sealed must have >= 5 seeds
    assert len(TIER_SEEDS[Tier.SEALED]) >= 5
    assert TIER_SEEDS[Tier.SEALED] == [901, 902, 903, 904, 905]


def test_seed_manifest_generation():
    manifest = generate_seed_manifest(Tier.VALIDATION)
    assert manifest.tier == Tier.VALIDATION
    assert len(manifest.seeds) >= 10
    assert len(manifest.dataset_hash) == 64  # SHA-256 hex digest
    assert manifest.spec_version == "1.0.0"


def test_run_validation_splits():
    res = run_seed_splits(tier=Tier.VALIDATION)
    assert res["tier"] == "validation"
    assert res["seed_count"] == 10
    assert "metrics_aggregate" in res
    assert "bootstrap_ci" in res
    assert res["runtime_seconds"] < 180.0  # Must be < 3 minutes SLA
