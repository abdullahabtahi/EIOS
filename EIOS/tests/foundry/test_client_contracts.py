"""Tests for client data product contracts (SC-002)."""

import pytest

from eios.foundry.contracts import (
    Client360Record,
    ContractValidationError,
    ContractValidator,
    DeviceNetworkEdge,
    FunnelEventRecord,
)
from eios.foundry.generators.client import ClientDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_client_data_products_pass_contracts():
    """Confirms client_360, client_funnel, and device_network_graph pass Layer 1 Pydantic contracts."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=100)
    generator = ClientDataGenerator(universe=universe, rng=rng)

    client_records = generator.generate_client_360()
    funnel_records = generator.generate_client_funnel()
    device_records = generator.generate_device_network()

    validator_360 = ContractValidator(Client360Record)
    validated_360 = validator_360.validate_batch(client_records)
    assert len(validated_360) == 100

    validator_funnel = ContractValidator(FunnelEventRecord)
    validated_funnel = validator_funnel.validate_batch(funnel_records)
    assert len(validated_funnel) >= 100

    validator_device = ContractValidator(DeviceNetworkEdge)
    validated_device = validator_device.validate_batch(device_records)
    assert len(validated_device) >= 100


def test_contract_validation_hard_fails_on_corrupt_record():
    """Confirms ContractValidationError is raised if a record violates schema."""
    validator = ContractValidator(Client360Record)
    bad_batch = [
        {
            "client_id": "CR123",
            "person_id": "bad-id",
            "country": "US",
            "kyc_tier": "INVALID_TIER",  # Breach!
            "created_at": "2026-01-01T00:00:00Z",
            "status": "ACTIVE",
            "mt5_login_id": 12345,
            "account_id": "CR123",
            "email": "test@example.com",
        }
    ]
    with pytest.raises(ContractValidationError):
        validator.validate_batch(bad_batch)
