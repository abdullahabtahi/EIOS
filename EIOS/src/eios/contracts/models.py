"""Pydantic v2 schemas for all 14 Layer 1 Data Products."""

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class BaseDataProductModel(BaseModel):
    """Base class for typed data product payloads."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Client360Event(BaseDataProductModel):
    """Data Product 1: client_360 (Grain: client_id, Freshness: 5m, Marking: P)."""
    client_id: str = Field(..., min_length=4)
    tax_id: str = Field(..., min_length=4)  # Marking P: Tokenized
    full_name: str = Field(..., min_length=2)  # Marking P: Tokenized
    email: str = Field(..., min_length=5)  # Marking P: Tokenized
    phone: str = Field(..., min_length=6)  # Marking P: Tokenized
    dob: date
    country: str = Field(..., min_length=2, max_length=3)
    kyc_status: Literal["PENDING", "APPROVED", "REJECTED", "EDD_REQUIRED"]
    kyc_approved_at: datetime | None = None
    partner_id: str | None = None
    declared_monthly_income: float | None = Field(default=None, ge=0.0)
    lifetime_value: float = Field(default=0.0)
    segment: str = Field(default="STANDARD")


class ClientFunnelEvent(BaseDataProductModel):
    """Data Product 2: client_funnel (Grain: client_id x stage, Freshness: 15m, Marking: P)."""
    client_id: str = Field(..., min_length=4)
    stage: Literal["REGISTRATION", "KYC_SUBMITTED", "KYC_VERIFIED", "FIRST_DEPOSIT", "FIRST_TRADE"]
    entered_at: datetime
    source: str = Field(default="DIRECT")
    utm_campaign: str | None = None


class TransactionAMLEvent(BaseDataProductModel):
    """Data Product 3: transactions_aml (Grain: txn_id, Freshness: 30s, Marking: P, S)."""
    txn_id: str = Field(..., min_length=6)
    client_id: str = Field(..., min_length=4)
    txn_type: Literal["DEPOSIT", "WITHDRAWAL", "TRANSFER", "ESCROW_RELEASE"]
    amount: float = Field(..., gt=0.0)
    currency: str = Field(..., min_length=3, max_length=5)
    payment_method_id: str = Field(..., min_length=3)
    payment_agent_id: str | None = None
    timestamp: datetime
    is_first_deposit: bool = False
    status: Literal["COMPLETED", "PENDING", "FAILED", "CANCELLED"] = "COMPLETED"


class TradingActivityEvent(BaseDataProductModel):
    """Data Product 4: trading_activity (Grain: trade_id, Freshness: 30s, Marking: P)."""
    trade_id: str = Field(..., min_length=6)
    client_id: str = Field(..., min_length=4)
    symbol: str = Field(..., min_length=2)  # e.g. "VOL_75", "BOOM_1000", "EURUSD"
    side: Literal["BUY", "SELL"]
    volume: float = Field(..., gt=0.0)
    open_price: float = Field(..., gt=0.0)
    close_price: float | None = None
    open_ts: datetime
    close_ts: datetime | None = None
    profit_loss: float | None = None


class DeviceGraphEdgeEvent(BaseDataProductModel):
    """Data Product 5: device_network_graph (Grain: edge_id, Freshness: 1m, Marking: P, S)."""
    edge_id: str = Field(..., min_length=6)
    source_id: str = Field(..., min_length=4)  # client_id
    target_id: str = Field(..., min_length=4)  # device_id or ip_id
    edge_type: Literal["USES_DEVICE", "CONNECTS_FROM_IP", "FUNDS_VIA"]
    first_seen: datetime
    last_seen: datetime
    session_count: int = Field(default=1, ge=1)
    is_shared_context: bool = False


class Partner360Event(BaseDataProductModel):
    """Data Product 6: partner_360 (Grain: partner_id, Freshness: 15m)."""
    partner_id: str = Field(..., min_length=4)
    tier: Literal["TIER_1", "TIER_2", "TIER_3", "VIP_MASTER"]
    region: str = Field(..., min_length=2)
    tenure_months: int = Field(default=0, ge=0)
    value_at_risk: float = Field(default=0.0, ge=0.0)
    manager_id: str | None = None
    status: Literal["ACTIVE", "DISENGAGED", "SUSPENDED", "CHURNED"] = "ACTIVE"


class ReferralTreeEdgeEvent(BaseDataProductModel):
    """Data Product 7: partner_referral_tree (Grain: parent x child, Freshness: 15m)."""
    parent_id: str = Field(..., min_length=4)
    child_id: str = Field(..., min_length=4)
    layer: int = Field(..., ge=1, le=5)
    attributed_master_id: str = Field(..., min_length=4)
    since: datetime


class CommissionLedgerEvent(BaseDataProductModel):
    """Data Product 8: commission_ledger (Grain: entry_id, Freshness: 15m)."""
    entry_id: str = Field(..., min_length=6)
    partner_id: str = Field(..., min_length=4)
    client_id: str = Field(..., min_length=4)
    basis: Literal["REVSHARE", "LOT_REBATE", "CPA_BONUS"]
    amount: float = Field(..., gt=0.0)
    currency: str = Field(default="USD", min_length=3, max_length=5)
    paid_at: datetime


class PartnerSignalsEvent(BaseDataProductModel):
    """Data Product 9: partner_engagement_signals (Grain: partner_id x date, Freshness: 1h)."""
    partner_id: str = Field(..., min_length=4)
    date: date
    logins: int = Field(default=0, ge=0)
    referrals: int = Field(default=0, ge=0)
    ftd_count: int = Field(default=0, ge=0)
    conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    clicks: int = Field(default=0, ge=0)


class PartnerCommsEvent(BaseDataProductModel):
    """Data Product 10: partner_comms (Grain: message_id, Freshness: 15m, Marking: S)."""
    message_id: str = Field(..., min_length=6)
    partner_id: str = Field(..., min_length=4)
    channel: Literal["TICKET", "EMAIL", "CHAT", "CALL_NOTE"]
    sentiment: Literal["POSITIVE", "NEUTRAL", "NEGATIVE", "ESCALATED"]
    text: str = Field(..., min_length=1)  # Untrusted text corpus
    timestamp: datetime


class FinancialPnLEvent(BaseDataProductModel):
    """Data Product 11: financial_pnl (Grain: date x prod x reg, Freshness: 1h)."""
    date: date
    product: str = Field(..., min_length=2)  # e.g. "SYNTHETICS_BBOOK", "FOREX_ABOOK"
    region: str = Field(..., min_length=2)
    revenue: float
    cost: float = Field(default=0.0, ge=0.0)
    net_margin: float
    ltv_cohort: str = Field(default="STANDARD")


class CompetitorBenchmarkEvent(BaseDataProductModel):
    """Data Product 12: competitor_benchmarks (Grain: comp x date x reg, Freshness: 24h)."""
    competitor: str = Field(..., min_length=2)
    date: date
    region: str = Field(..., min_length=2)
    payout_rate: float = Field(..., ge=0.0, le=1.0)
    spread_pips: float = Field(..., ge=0.0)
    promo_event: str | None = None


class PlatformOperationsEvent(BaseDataProductModel):
    """Data Product 13: platform_operations (Grain: date x service, Freshness: 5m)."""
    date: date
    service: str = Field(..., min_length=2)
    latency_p95_ms: float = Field(..., ge=0.0)
    incidents_count: int = Field(default=0, ge=0)
    escrow_disputes_count: int = Field(default=0, ge=0)
    uptime_percentage: float = Field(default=100.0, ge=0.0, le=100.0)


class ComplianceCaseEvent(BaseDataProductModel):
    """Data Product 14: compliance_cases (Grain: case_id, Freshness: 1m, Marking: S)."""
    case_id: str = Field(..., min_length=6)
    client_id: str = Field(..., min_length=4)
    status: Literal["OPEN", "INVESTIGATING", "SAR_FILED", "CLOSED_BENIGN"]
    typology: Literal["STRUCTURING_BURST", "OPPOSITE_TRADING", "SYNTHETIC_RING", "BONUS_ABUSE"]
    analyst_id: str | None = None
    risk_score: float = Field(..., ge=0.0, le=100.0)
    created_at: datetime
    updated_at: datetime
