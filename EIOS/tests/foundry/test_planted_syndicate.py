"""Tests for planted 47-account syndicate ring and round-trip laundering typology (SC-005, FR-019, FR-020)."""

import json
from pathlib import Path
import pytest
from eios.foundry.generators.aml import AMLDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.storage.eval_truth_store import EvalGroundTruthStore
from eios.foundry.universe import GlobalEntityUniverse


def test_planted_47_account_syndicate_topology(tmp_path: Path):
    """Confirms syndicate_47.json contains exactly 47 accounts, 6 devices, 4 IPs, and round-trip events."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=200)
    truth_store = EvalGroundTruthStore(base_dir=tmp_path / "eval-truth")
    aml_gen = AMLDataGenerator(universe=universe, rng=rng, truth_store=truth_store)

    aml_gen.inject_syndicate_ring_and_round_trip()

    syndicate_truth_path = tmp_path / "eval-truth" / "module_a" / "syndicate_47.json"
    assert syndicate_truth_path.exists(), "Syndicate truth file missing from eval-truth bucket"

    with open(syndicate_truth_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data["client_uuids"]) == 47, f"Expected 47 clients, found {len(data['client_uuids'])}"
    assert len(data["device_hashes"]) == 6, f"Expected 6 devices, found {len(data['device_hashes'])}"
    assert len(data["ip_addresses"]) == 4, f"Expected 4 IPs, found {len(data['ip_addresses'])}"
    assert len(data["round_trip_transaction_ids"]) >= 47, "Must track round-trip laundering transaction IDs"

    # Check typology description and round-trip characteristics
    assert data["typology"] == "ROUND_TRIP_LAUNDERING_RING"
    assert data["deposit_amount"] == 500.00
    assert data["micro_trade_amount"] == 0.01
