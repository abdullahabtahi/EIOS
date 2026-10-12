"""Tests for deterministic PRNG and stream spawning (F01)."""

import pytest
import numpy as np
from eios.foundry.rng import RNGManager


def test_rng_manager_deterministic_streams() -> None:
    """Verify that same seed produces identical streams across instances."""
    rng1 = RNGManager(seed=42)
    rng2 = RNGManager(seed=42)

    floats1 = rng1.get_generator("domain_a").random(size=100)
    floats2 = rng2.get_generator("domain_a").random(size=100)

    np.testing.assert_array_equal(floats1, floats2)


def test_rng_manager_spawn_independence() -> None:
    """Verify that spawned streams for different domains are statistically distinct."""
    rng = RNGManager(seed=42)

    gen_a = rng.get_generator("domain_a")
    gen_b = rng.get_generator("domain_b")

    floats_a = gen_a.random(size=50)
    floats_b = gen_b.random(size=50)

    assert not np.array_equal(floats_a, floats_b)


def test_rng_manager_faker_seed_derivation() -> None:
    """Verify Faker seed derivation from master SeedSequence."""
    rng1 = RNGManager(seed=42)
    rng2 = RNGManager(seed=42)

    seed_a1 = rng1.derive_faker_seed("client")
    seed_a2 = rng2.derive_faker_seed("client")
    seed_b1 = rng1.derive_faker_seed("partner")

    assert seed_a1 == seed_a2
    assert seed_a1 != seed_b1
