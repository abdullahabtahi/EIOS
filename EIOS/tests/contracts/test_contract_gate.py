"""Tests for Contract Validation Gate across all 14 Layer 1 Data Products."""

from datetime import UTC, datetime

import pytest

from eios.contracts.base import DataProductEnum
from eios.ingestion.validator import ContractValidator


@pytest.fixture
def validator() -> ContractValidator:
    return ContractValidator()


def test_validator_accepts_valid_transaction_aml(validator: ContractValidator):
    valid_payload = {
        "txn_id": "txn_100001",
        "client_id": "cli_9999",
        "txn_type": "DEPOSIT",
        "amount": 1500.50,
        "currency": "USD",
        "payment_method_id": "pm_visa_01",
        "timestamp": datetime.now(UTC).isoformat(),
        "is_first_deposit": False,
        "status": "COMPLETED",
    }
    result = validator.validate(DataProductEnum.TRANSACTIONS_AML, valid_payload)
    assert result.is_valid is True
    assert result.errors == []
    assert result.validated_model is not None
    assert result.validated_model.amount == 1500.50


def test_validator_rejects_missing_required_field(validator: ContractValidator):
    invalid_payload = {
        "txn_id": "txn_100002",
        # Missing client_id
        "txn_type": "WITHDRAWAL",
        "amount": 250.0,
        "currency": "USD",
        "payment_method_id": "pm_bank_01",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    result = validator.validate(DataProductEnum.TRANSACTIONS_AML, invalid_payload)
    assert result.is_valid is False
    assert len(result.errors) > 0
    assert any("client_id" in err.field_path for err in result.errors)


def test_validator_rejects_range_breach_negative_amount(validator: ContractValidator):
    invalid_payload = {
        "txn_id": "txn_100003",
        "client_id": "cli_9999",
        "txn_type": "DEPOSIT",
        "amount": -50.0,  # gt=0.0 violation
        "currency": "USD",
        "payment_method_id": "pm_bank_01",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    result = validator.validate(DataProductEnum.TRANSACTIONS_AML, invalid_payload)
    assert result.is_valid is False
    assert any("amount" in err.field_path for err in result.errors)


def test_validator_rejects_schema_type_error(validator: ContractValidator):
    invalid_payload = {
        "txn_id": "txn_100004",
        "client_id": "cli_9999",
        "txn_type": "INVALID_TYPE",  # not in Literal["DEPOSIT", "WITHDRAWAL", ...]
        "amount": 100.0,
        "currency": "USD",
        "payment_method_id": "pm_bank_01",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    result = validator.validate(DataProductEnum.TRANSACTIONS_AML, invalid_payload)
    assert result.is_valid is False
    assert any("txn_type" in err.field_path for err in result.errors)


def test_validator_supports_all_14_data_products(validator: ContractValidator):
    assert len(validator.supported_products) == 14
    for product in DataProductEnum:
        assert product in validator.supported_products
