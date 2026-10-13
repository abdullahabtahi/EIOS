"""Tests for KYC recency burst suspicious transaction clustering (FR-021)."""

from eios.foundry.generators.aml import AMLDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_kyc_recency_burst_clustering():
    """Confirms suspicious transaction bursts for flagged accounts are concentrated within 72h of KYC approval."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=200)
    aml_gen = AMLDataGenerator(universe=universe, rng=rng)

    burst_events = aml_gen.generate_kyc_burst_transactions(burst_account_count=10)
    assert len(burst_events) >= 30  # At least 3+ rapid txs per burst account

    for tx in burst_events:
        assert tx["time_since_kyc_approval_hours"] is not None
        assert 0.0 <= tx["time_since_kyc_approval_hours"] <= 72.0, (
            f"Transaction occurred outside 72h window: {tx['time_since_kyc_approval_hours']}h"
        )
