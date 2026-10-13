"""Tests for Foundry Pydantic contract batch validation gate."""

import pytest
from pydantic import BaseModel, Field

from eios.foundry.contracts import ContractValidationError, ContractValidator


class SampleClientRecord(BaseModel):
    client_id: str
    kyc_level: int = Field(ge=0, le=3)
    balance: float = Field(ge=0.0)


def test_contract_validator_success() -> None:
    validator = ContractValidator(SampleClientRecord)
    records = [
        {"client_id": "c1", "kyc_level": 1, "balance": 100.5},
        {"client_id": "c2", "kyc_level": 2, "balance": 0.0},
    ]
    validated = validator.validate_batch(records)
    assert len(validated) == 2
    assert validated[0].client_id == "c1"


def test_contract_validator_failure_raises_contract_error() -> None:
    validator = ContractValidator(SampleClientRecord)
    records = [
        {"client_id": "c1", "kyc_level": 99, "balance": -50.0},
    ]
    with pytest.raises(ContractValidationError) as exc_info:
        validator.validate_batch(records)

    assert "kyc_level" in str(exc_info.value)
