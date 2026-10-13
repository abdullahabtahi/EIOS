"""Tests for deliberate S-07 contract breach injection (SC-007, T058, T061)."""

import pytest

from eios.foundry.contracts import (
    Client360Record,
    ContractValidationError,
    ContractValidator,
    TransactionAMLRecord,
)
from eios.foundry.noise.breach_injector import BreachInjector
from eios.foundry.rng import DeterministicRNG


def test_breach_injector_triggers_contract_validation_error():
    """Confirms injected contract breaches loudly fail Layer 1 Pydantic contracts (SC-007)."""
    rng = DeterministicRNG(master_seed=42)
    injector = BreachInjector(rng=rng)

    valid_tx = {
        "transaction_id": "TX-00000001",
        "account_id": "CR1000001",
        "direction": "DEPOSIT",
        "amount": "100.00",
        "currency": "USD",
        "payment_method_id": "PM-0001",
        "ip_address": "198.51.100.1",
        "device_hash": "devhash_1",
        "timestamp": "2025-01-01T00:00:00Z",
    }

    # Inject negative amount breach
    breached_tx_batch = injector.inject_transaction_breaches(
        [valid_tx], breach_type="NEGATIVE_AMOUNT"
    )
    validator_tx = ContractValidator(TransactionAMLRecord)

    with pytest.raises(ContractValidationError):
        validator_tx.validate_batch(breached_tx_batch)

    # Inject invalid status in client_360
    valid_client = {
        "client_id": "CR1000001",
        "person_id": "00000000-0000-0000-0000-000000000001",
        "country": "SG",
        "kyc_tier": "TIER_1_IDENTITY",
        "created_at": "2025-01-01T00:00:00Z",
        "status": "ACTIVE",
        "mt5_login_id": 10000001,
        "account_id": "CR1000001",
        "email": "test@example.com",
    }

    breached_client_batch = injector.inject_client_breaches(
        [valid_client], breach_type="INVALID_STATUS"
    )
    validator_client = ContractValidator(Client360Record)

    with pytest.raises(ContractValidationError):
        validator_client.validate_batch(breached_client_batch)
