"""Deterministic PRNG stream manager using numpy.random.SeedSequence and PCG64."""

from __future__ import annotations

import hashlib

import numpy as np


class RNGManager:
    """Manages independent, deterministic pseudo-random number generator streams."""

    def __init__(self, seed: int | None = None, *, master_seed: int | None = None) -> None:
        actual_seed = seed if seed is not None else (master_seed if master_seed is not None else 42)
        self.master_seed = actual_seed
        self._seed_sequence = np.random.SeedSequence(actual_seed)
        self._generators: dict[str, np.random.Generator] = {}

    def get_generator(self, domain_name: str) -> np.random.Generator:
        """Returns or creates a deterministic Generator for a named domain."""
        if domain_name not in self._generators:
            # Deterministically derive child SeedSequence using spawn_key from domain name hash
            domain_words = tuple(
                int(b) for b in hashlib.sha256(domain_name.encode("utf-8")).digest()[:4]
            )
            child_seq = np.random.SeedSequence(self.master_seed, spawn_key=domain_words)
            bit_gen = np.random.PCG64(child_seq)
            self._generators[domain_name] = np.random.Generator(bit_gen)
        return self._generators[domain_name]

    def derive_faker_seed(self, domain_name: str) -> int:
        """Derives a deterministic integer seed suitable for seeding Faker instances."""
        gen = self.get_generator(f"faker_{domain_name}")
        return int(gen.integers(1, 2**31 - 1))


DeterministicRNG = RNGManager
