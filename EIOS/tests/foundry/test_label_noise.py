"""Tests for analyst label noise injection and ambiguity rate bounds (FR-050)."""

import pytest
from eios.foundry.noise.label_noise import inject_analyst_label_noise
from eios.foundry.rng import DeterministicRNG


def test_analyst_label_noise_bounds():
    """Confirms label noise flips between 3.0% and 8.0% of analyst decisions."""
    rng = DeterministicRNG(master_seed=42)

    # 1000 base compliance cases
    base_cases = [
        {"case_id": f"CASE-{i:06d}", "analyst_decision": "DISMISS", "is_true_positive": False}
        for i in range(1000)
    ]

    noisy_cases = inject_analyst_label_noise(base_cases, rng=rng)
    assert len(noisy_cases) == 1000

    # Count flips
    flipped_count = sum(
        1 for orig, noisy in zip(base_cases, noisy_cases)
        if orig["analyst_decision"] != noisy["analyst_decision"]
    )
    flip_rate = (flipped_count / len(base_cases)) * 100.0

    assert 3.0 <= flip_rate <= 8.0, f"Flip rate {flip_rate:.2f}% outside [3.0%, 8.0%] range"
