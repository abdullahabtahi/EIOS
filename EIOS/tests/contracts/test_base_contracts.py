"""Unit tests for EIOS Layer 1 Base Contracts and Enums."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from eios.contracts.base import (
    DataProductEnum,
    DataProductEvent,
    TenantEnum,
)


def test_data_product_enum_membership():
    """Verify all 14 Layer 1 data products are members of DataProductEnum."""
    expected_products = {
        "client_360",
        "client_funnel",
        "transactions_aml",
        "trading_activity",
        "device_network_graph",
        "partner_360",
        "partner_referral_tree",
        "commission_ledger",
        "partner_engagement_signals",
        "partner_comms",
        "financial_pnl",
        "competitor_benchmarks",
        "platform_operations",
        "compliance_cases",
    }
    actual_products = {p.value for p in DataProductEnum}
    assert actual_products == expected_products
    assert len(DataProductEnum) == 14


def test_tenant_enum_membership():
    """Verify the 3 legal jurisdictions / regulatory tenants."""
    expected_tenants = {"DERIV_MFSA", "DERIV_LFSA", "DERIV_VFSC"}
    actual_tenants = {t.value for t in TenantEnum}
    assert actual_tenants == expected_tenants


def test_valid_data_product_event_parsing():
    """Verify parsing a valid DataProductEvent envelope."""
    payload_dict = {
        "event_id": "11111111-2222-3333-4444-555555555555",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "DERIV_MFSA",
        "payload": {"trade_id": "T001", "symbol": "BOOM_1000", "volume": 1.0},
    }
    event = DataProductEvent.model_validate(payload_dict)
    assert str(event.event_id) == "11111111-2222-3333-4444-555555555555"
    assert event.product_name == DataProductEnum.TRADING_ACTIVITY
    assert event.tenant_id == TenantEnum.DERIV_MFSA
    assert event.event_timestamp == datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
    assert event.payload["trade_id"] == "T001"


def test_invalid_tenant_rejected():
    """Verify that an unapproved tenant ID raises validation error."""
    payload_dict = {
        "event_id": "11111111-2222-3333-4444-555555555555",
        "product_name": "trading_activity",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "UNAUTHORIZED_OFFSHORE_BROKER",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        DataProductEvent.model_validate(payload_dict)


def test_invalid_product_name_rejected():
    """Verify that an unknown product name raises validation error."""
    payload_dict = {
        "event_id": "11111111-2222-3333-4444-555555555555",
        "product_name": "non_existent_product",
        "schema_version": "1.0.0",
        "event_timestamp": "2026-10-04T12:00:00Z",
        "tenant_id": "DERIV_MFSA",
        "payload": {},
    }
    with pytest.raises(ValidationError):
        DataProductEvent.model_validate(payload_dict)
