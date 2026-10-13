"""Tests for partner fraud patterns: 3-tier syndicate, mirror trading, bot traffic, bonus abuse (FR-026 to FR-034, SC-005)."""

import json
from pathlib import Path

import pytest

from eios.foundry.generators.partner import PartnerDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.storage.eval_truth_store import EvalGroundTruthStore
from eios.foundry.universe import GlobalEntityUniverse


def test_partner_fraud_typologies_and_eval_truth(tmp_path: Path):
    """Verifies 3-tier ring (7/23/184), 23 mirror pairs, 12 bot partners, and 35% bonus abuse."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=500, partner_count=200)
    truth_store = EvalGroundTruthStore(base_dir=tmp_path / "eval-truth")
    gen = PartnerDataGenerator(universe=universe, rng=rng, truth_store=truth_store)

    fraud_data = gen.generate_partner_fraud_suite()
    truth_store_path = tmp_path / "eval-truth" / "module_b" / "partner_ring_7_23_184.json"

    assert truth_store_path.exists(), "Partner ring ground truth must exist"
    with open(truth_store_path, encoding="utf-8") as f:
        ring_truth = json.load(f)

    # 1. 3-tier ring verification
    assert len(ring_truth["master_partner_ids"]) == 7, "Must contain exactly 7 master partners"
    assert len(ring_truth["sub_partner_ids"]) == 23, "Must contain exactly 23 sub-partners"
    assert len(ring_truth["referred_client_ids"]) == 184, (
        "Must contain exactly 184 referred clients"
    )

    # 2. 23 Mirror trading pairs
    mirror_pairs = fraud_data["mirror_pairs"]
    assert len(mirror_pairs) == 23, "Must contain exactly 23 mirror trading pairs"
    for pair in mirror_pairs:
        assert pair["timing_correlation"] >= 0.89
        assert abs(pair["net_client_pnl"]) <= 0.50  # net client PnL approaches zero
        assert pair["commission_extracted"] > 0.0

    # 3. 12 Bot-traffic partners
    bot_partners = fraud_data["bot_partners"]
    assert len(bot_partners) == 12, "Must contain exactly 12 bot-traffic partners"
    for bp in bot_partners:
        assert bp["click_to_signup_conversion"] > 0.90  # Impossible conversion

    # 4. 35% Bonus abuse share
    bonus_abuse = fraud_data["bonus_abuse"]
    assert pytest.approx(bonus_abuse["bonus_abuse_share"], abs=0.05) == 0.35
