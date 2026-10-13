"""Pydantic v2 contract batch validation gate and core data product models."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class ContractValidationError(Exception):
    """Raised when a generated record batch fails Layer 1 contract validation."""

    pass


T = TypeVar("T", bound=BaseModel)


class ContractValidator(Generic[T]):  # noqa: UP046
    """Vectorized batch validator enforcing Pydantic contracts at generation time."""

    def __init__(self, model_cls: type[T]) -> None:
        self.model_cls = model_cls
        self.adapter = TypeAdapter(list[model_cls])

    def validate_batch(self, records: list[dict[str, Any]]) -> list[T]:
        """Validates a batch of raw records against the model schema.

        Raises ContractValidationError immediately on schema breach.
        """
        try:
            return self.adapter.validate_python(records)
        except ValidationError as e:
            raise ContractValidationError(
                f"L1 Contract violation for model {self.model_cls.__name__}: {e}"
            ) from e


# ---------------------------------------------------------------------------
# Core Layer 1 Data Product Pydantic Contracts
# ---------------------------------------------------------------------------


class BaseContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Client360Record(BaseContractModel):
    client_id: str
    person_id: str
    country: str
    kyc_tier: Literal["TIER_0_UNVERIFIED", "TIER_1_IDENTITY", "TIER_2_ADDRESS", "TIER_3_ENHANCED"]
    kyc_approved_at: str | None = None
    created_at: str
    status: Literal["ACTIVE", "SUSPENDED", "CLOSED"]
    mt5_login_id: int
    account_id: str
    email: str
    has_identity_duplicate_noise: bool = False


class FunnelEventRecord(BaseContractModel):
    event_id: str
    client_id: str
    step: Literal["VISIT", "SIGNUP", "KYC_SUBMIT", "FIRST_DEPOSIT"]
    timestamp: str


class DeviceNetworkEdge(BaseContractModel):
    edge_id: str
    client_id: str
    device_hash: str
    ip_address: str
    is_hub: bool = False
    timestamp: str


class TransactionAMLRecord(BaseContractModel):
    transaction_id: str
    account_id: str
    mt5_login_id: int | None = None
    direction: Literal["DEPOSIT", "WITHDRAWAL", "INTERNAL_TRANSFER"]
    amount: Decimal = Field(gt=Decimal("0.0"))
    currency: str = "USD"
    payment_method_id: str
    ip_address: str
    device_hash: str
    timestamp: str
    time_since_kyc_approval_hours: float | None = None


class TradeExecutionRecord(BaseContractModel):
    deal_id: str
    mt5_login_id: int
    symbol: str
    side: Literal["BUY", "SELL"]
    volume_lots: Decimal = Field(gt=Decimal("0.0"))
    open_price: Decimal
    close_price: Decimal
    open_time: str
    close_time: str
    profit_loss: Decimal
    commission_paid: Decimal


class ComplianceCaseRecord(BaseContractModel):
    case_id: str
    account_id: str
    alert_type: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    is_true_positive: bool
    analyst_decision: Literal["ESCALATE", "DISMISS", "SAR_FILED"] | None = None
    created_at: str


class Partner360Record(BaseContractModel):
    partner_id: str
    person_id: str
    referral_code: str
    parent_partner_id: str | None = None
    commission_tier: Literal["STANDARD", "VIP", "MASTER"]
    joined_at: str
    is_bot_fraud: bool = False


class ReferralNodeRecord(BaseContractModel):
    link_id: str
    parent_partner_id: str
    child_partner_id: str | None = None
    referred_client_id: str | None = None
    tier_depth: int = Field(ge=1, le=3)
    created_at: str


class CommissionLedgerRecord(BaseContractModel):
    ledger_id: str
    partner_id: str
    client_account_id: str
    deal_id_ref: str
    commission_amount: Decimal = Field(gt=Decimal("0.0"))
    calculation_tier: int = Field(ge=1, le=3)
    timestamp: str


class WeeklySignalRecord(BaseContractModel):
    signal_id: str
    partner_id: str
    week_start_date: str
    active_traders_count: int = Field(ge=0)
    weekly_ftd_count: int = Field(ge=0)
    click_to_signup_conversion: float = Field(ge=0.0)
    weekly_logins: int = Field(ge=0)
    average_ticket_sentiment: float = Field(ge=-1.0, le=1.0)
    poaching_language_flags: int = Field(ge=0)


class PartnerCommsRecord(BaseContractModel):
    ticket_id: str
    partner_id: str
    sender_role: Literal["PARTNER", "ACCOUNT_MANAGER", "SUPPORT"]
    subject: str
    body_text: str = Field(min_length=5, max_length=5000)
    created_at: str


class DailyPnLRecord(BaseContractModel):
    date: str
    gross_trading_revenue: Decimal
    net_spread_revenue: Decimal
    partner_commission_expense: Decimal
    operational_infrastructure_cost: Decimal
    net_ebitda: Decimal


class CompetitorEventRecord(BaseContractModel):
    event_id: str
    competitor_alias: str
    event_type: Literal["PAYOUT_INCREASE", "SPREAD_CUT", "PROMO_CAMPAIGN", "ACQUISITION"]
    delta_value: float
    timestamp: str


class OperationalMetricRecord(BaseContractModel):
    timestamp: str
    service_name: str
    p95_latency_ms: float = Field(ge=0.0)
    dispute_ticket_count: int = Field(ge=0)
    error_rate: float = Field(ge=0.0, le=1.0)
    is_incident_active: bool = False
