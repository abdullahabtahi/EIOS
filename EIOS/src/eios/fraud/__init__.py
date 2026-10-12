"""Partner & Affiliate Fraud Sentinel package (Module B / Slice S3).

Detects coordinated opposite/mirror trading, multi-tier sub-affiliate rings,
bonus harvesting, client recycling, and bot traffic anomalies.
"""

from eios.fraud.models import (
    BonusAbuseProfile,
    DirectionalType,
    FraudTypology,
    PartnerFraudCase,
    RecyclingCluster,
    ReferralRingNode,
    RingAttribution,
    TradingPairCorrelation,
    TrafficAnomalySignal,
)

__all__ = [
    "DirectionalType",
    "FraudTypology",
    "TradingPairCorrelation",
    "ReferralRingNode",
    "RingAttribution",
    "BonusAbuseProfile",
    "RecyclingCluster",
    "TrafficAnomalySignal",
    "PartnerFraudCase",
]
