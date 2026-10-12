"""Tests for Module A AML data product schema compliance (SC-002, FR-017, FR-025)."""

import pytest
from eios.foundry.contracts import (
    ComplianceCaseRecord,
    ContractValidator,
    TradeExecutionRecord,
    TransactionAMLRecord,
)
from eios.foundry.generators.aml import AMLDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_aml_contracts_pass_layer1_validation():
    """Confirms transactions_aml, trading_activity, and compliance_cases pass Pydantic models."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=200)
    aml_gen = AMLDataGenerator(universe=universe, rng=rng)

    transactions = aml_gen.generate_transactions(count=100)
    trades = aml_gen.generate_trades(count=100)
    alerts = aml_gen.generate_compliance_cases(count=50)

    validator_tx = ContractValidator(TransactionAMLRecord)
    validated_tx = validator_tx.validate_batch(transactions)
    assert len(validated_tx) == 100

    validator_trade = ContractValidator(TradeExecutionRecord)
    validated_trade = validator_trade.validate_batch(trades)
    assert len(validated_trade) == 100

    validator_case = ContractValidator(ComplianceCaseRecord)
    validated_case = validator_case.validate_batch(alerts)
    assert len(validated_case) == 50
