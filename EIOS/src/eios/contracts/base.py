"""Base contract models, enums, and event envelopes for EIOS Layer 1."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class TenantEnum(str, Enum):
    """Regulatory jurisdictions / legal entities."""

    DERIV_MFSA = "DERIV_MFSA"
    DERIV_LFSA = "DERIV_LFSA"
    DERIV_VFSC = "DERIV_VFSC"


class DataProductEnum(str, Enum):
    """The 14 governed Layer 1 Data Products."""

    CLIENT_360 = "client_360"
    CLIENT_FUNNEL = "client_funnel"
    TRANSACTIONS_AML = "transactions_aml"
    TRADING_ACTIVITY = "trading_activity"
    DEVICE_NETWORK_GRAPH = "device_network_graph"
    PARTNER_360 = "partner_360"
    PARTNER_REFERRAL_TREE = "partner_referral_tree"
    COMMISSION_LEDGER = "commission_ledger"
    PARTNER_ENGAGEMENT_SIGNALS = "partner_engagement_signals"
    PARTNER_COMMS = "partner_comms"
    FINANCIAL_PNL = "financial_pnl"
    COMPETITOR_BENCHMARKS = "competitor_benchmarks"
    PLATFORM_OPERATIONS = "platform_operations"
    COMPLIANCE_CASES = "compliance_cases"


def ensure_utc(dt: datetime) -> datetime:
    """Ensure timestamp has explicit UTC timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class DataProductEvent(BaseModel):
    """Universal envelope for operational telemetry events."""

    event_id: UUID = Field(default_factory=uuid4)
    product_name: DataProductEnum
    schema_version: str = Field(default="1.0.0")
    event_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: TenantEnum
    payload: dict[str, Any]
    source_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_timestamp")
    @classmethod
    def _validate_utc(cls, v: datetime) -> datetime:
        return ensure_utc(v)
