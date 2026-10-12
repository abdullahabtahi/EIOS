"""13 Canonical Kinetic Ontology Object Types per docs/foundry.md and data-model.md."""

from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from eios.ontology.core.base import OntologyObject
from eios.ontology.core.interfaces import AuditableEntity, TransactingEntity


class ClientAccount(OntologyObject, TransactingEntity):
    """Core retail/institutional client trading account entity."""

    client_id: str
    kyc_status: str = "PENDING"
    kyc_approved_at: datetime | None = None
    segment: str = "STANDARD"
    region_id: str | None = None
    lifetime_value_usd: float = 0.0
    partner_id: str | None = None

    @property
    def primary_key(self) -> str:
        return self.client_id

    def get_total_volume(self, window: str = "30d") -> float:
        return self.lifetime_value_usd

    def get_net_flow(self, window: str = "30d") -> float:
        return self.lifetime_value_usd * 0.4

    def get_risk_rating(self) -> str:
        if self.segment == "VIP":
            return "LOW"
        return "MEDIUM"


class Device(OntologyObject):
    """Device fingerprint entity used by client sessions."""

    device_id: str
    device_fingerprint: str = ""
    os: str = ""
    browser: str = ""
    is_shared_context: bool = False
    degree: int = 0

    @property
    def primary_key(self) -> str:
        return self.device_id


class IPAddress(OntologyObject):
    """IP Address entity representing network ingress origin."""

    ip_id: str
    ip_address: str = ""
    asn: str = ""
    country_code: str = ""
    is_datacenter: bool = False
    is_vpn: bool = False
    is_shared_context: bool = False
    degree: int = 0

    @property
    def primary_key(self) -> str:
        return self.ip_id


class PaymentMethod(OntologyObject):
    """Funding rails and accounts (cards, e-wallets, crypto)."""

    payment_method_id: str
    method_type: str = "UNKNOWN"
    provider: str = "UNKNOWN"
    tokenized_account: str = ""
    risk_tier: str = "STANDARD"

    @property
    def primary_key(self) -> str:
        return self.payment_method_id


class Partner(OntologyObject, TransactingEntity):
    """Affiliate or Introducing Broker (IB) partner entity."""

    partner_id: str
    tier: str = "TIER_2"
    region_id: str | None = None
    tenure_days: int = 0
    value_at_risk_usd: float = 0.0
    manager_id: str | None = None

    # Churn Radar dynamic kinetic properties (Slice S2)
    hazard_probability_30d: float = 0.0
    priority_score: float = 0.0
    risk_tier: str = "LOW"
    intervention_window: str = "STABLE"
    change_point_flag: bool = False
    churn_explanation: str | None = None

    @property
    def primary_key(self) -> str:
        return self.partner_id

    def get_total_volume(self, window: str = "30d") -> float:
        return self.value_at_risk_usd * 2.5

    def get_net_flow(self, window: str = "30d") -> float:
        return self.value_at_risk_usd

    def get_risk_rating(self) -> str:
        if self.risk_tier in ["HIGH", "MEDIUM"]:
            return self.risk_tier
        if self.tier == "TIER_1":
            return "HIGH"  # Higher value at risk requires vigilance
        return "LOW"


class SubAffiliate(OntologyObject):
    """Multi-tier sub-partner in a referral tree."""

    sub_affiliate_id: str
    parent_partner_id: str
    attribution_layer: int = 1
    registered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def primary_key(self) -> str:
        return self.sub_affiliate_id


class Competitor(OntologyObject):
    """Market competitor benchmarks and intelligence."""

    competitor_id: str
    name: str
    payout_rate_estimate: float = 0.0
    primary_region_id: str | None = None

    @property
    def primary_key(self) -> str:
        return self.competitor_id


class Product(OntologyObject):
    """Trading product offerings (e.g. Deriv MT5, Deriv Bot, Deriv Trader)."""

    product_id: str
    name: str
    category: str = "CFD"
    target_margin: float = 0.05

    @property
    def primary_key(self) -> str:
        return self.product_id


class Region(OntologyObject):
    """Geographic and regulatory jurisdiction boundary."""

    region_id: str
    name: str
    regulatory_tier: str = "TIER_1"

    @property
    def primary_key(self) -> str:
        return self.region_id


class Case(OntologyObject, AuditableEntity):
    """AML, fraud, or compliance investigation case."""

    case_id: str
    target_id: str
    status: str = "OPEN"
    typology: str = "UNKNOWN"
    assigned_analyst: str = "UNASSIGNED"
    risk_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def primary_key(self) -> str:
        return self.case_id

    def get_audit_trail(self) -> list[dict[str, Any]]:
        return [
            {
                "event": "CASE_CREATED",
                "status": self.status,
                "timestamp": self.created_at.isoformat(),
            },
            {
                "event": "LAST_UPDATED",
                "status": self.status,
                "timestamp": self.updated_at.isoformat(),
            },
        ]

    def get_security_markings(self) -> list[str]:
        return [m.value for m in self.markings]


class Alert(OntologyObject, AuditableEntity):
    """Real-time financial crime or behavioral alert."""

    alert_id: str
    case_id: str | None = None
    rule_name: str
    confidence_score: float = 0.0
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def primary_key(self) -> str:
        return self.alert_id

    def get_audit_trail(self) -> list[dict[str, Any]]:
        return [
            {"event": "ALERT_TRIGGERED", "rule": self.rule_name, "score": self.confidence_score}
        ]

    def get_security_markings(self) -> list[str]:
        return [m.value for m in self.markings]


class Decision(OntologyObject, AuditableEntity):
    """Human approval decision logged to the tamper-evident ledger."""

    decision_id: str
    action_intent_id: str
    outcome: str = "PENDING"
    approver_id: str
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ledger_seq: int = 0
    prev_hash: str = ""

    @property
    def primary_key(self) -> str:
        return self.decision_id

    def get_audit_trail(self) -> list[dict[str, Any]]:
        return [
            {
                "decision_id": self.decision_id,
                "outcome": self.outcome,
                "approver": self.approver_id,
                "seq": self.ledger_seq,
            }
        ]

    def get_security_markings(self) -> list[str]:
        return [m.value for m in self.markings]


class MacroEvent(OntologyObject):
    """Exogenous macro shock or regulatory shift affecting partner/regional dynamics."""

    event_id: str
    event_type: str
    description: str = ""
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    shock_intensity: float = 0.0

    @property
    def primary_key(self) -> str:
        return self.event_id
