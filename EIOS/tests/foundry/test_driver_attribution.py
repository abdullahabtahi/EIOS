"""Tests for ground-truth forecast driver attribution sum constraint (SC-008, FR-049)."""

from pathlib import Path

import pytest

from eios.foundry.generators.causal_truth import CausalTruthGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.storage.eval_truth_store import EvalGroundTruthStore


def test_driver_attribution_sum_constraint(tmp_path: Path):
    """Verifies that counterfactual forecast drivers sum to exactly 100.0%."""
    rng = DeterministicRNG(master_seed=42)
    truth_store = EvalGroundTruthStore(base_dir=tmp_path / "eval-truth")
    causal_gen = CausalTruthGenerator(rng=rng, truth_store=truth_store)

    drivers = causal_gen.generate_forecast_driver_attribution()

    assert "forecast_miss_drivers" in drivers
    driver_splits = drivers["forecast_miss_drivers"]

    # Sum of percentage contributions must be exactly 100.0%
    total_percentage = sum(driver_splits.values())
    assert pytest.approx(total_percentage, abs=1e-5) == 100.0, (
        f"Driver attribution must sum to 100.0%, got {total_percentage}"
    )

    # Core categories verified
    for category in ["competitive", "partner", "operational"]:
        assert category in driver_splits
        assert driver_splits[category] > 0.0
