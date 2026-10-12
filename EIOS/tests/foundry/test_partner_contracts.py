"""Tests for Partner Layer 1 data product contracts (T064, FR-026, FR-034)."""

import pytest
from eios.foundry.contracts import (
    CommissionLedgerRecord,
    ContractValidator,
    Partner360Record,
    ReferralNodeRecord,
)
from eios.foundry.generators.partner import PartnerDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_partner_data_products_pass_contracts():
    """Confirms partner_360, partner_referral_tree, and commission_ledger pass Layer 1 contracts."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=200, partner_count=50)
    gen = PartnerDataGenerator(universe=universe, rng=rng)

    p360_records = gen.generate_partner_360()
    tree_records = gen.generate_referral_tree()
    ledger_records = gen.generate_commission_ledger(count=100)

    validator_360 = ContractValidator(Partner360Record)
    validated_360 = validator_360.validate_batch(p360_records)
    assert len(validated_360) == 50

    validator_tree = ContractValidator(ReferralNodeRecord)
    validated_tree = validator_tree.validate_batch(tree_records)
    assert len(validated_tree) > 0

    validator_ledger = ContractValidator(CommissionLedgerRecord)
    validated_ledger = validator_ledger.validate_batch(ledger_records)
    assert len(validated_ledger) == 100
