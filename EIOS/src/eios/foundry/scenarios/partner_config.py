"""Configuration and fixed identities of the seeded partner world (spec 032 FR-001, FR-003).

The world is a pure function of this config. Named partners keep the identities the cockpit and the golden cases
already use (id, name, tier, market); every number about them is generated and then computed by the engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from eios.foundry.scenarios.aml_config import STORY_PARTNER as AML_RING_PARTNER

DEFAULT_SEED = 20261014
DEFAULT_AS_OF = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
STORY_PARTNER = "PTR-882"  # the partner the golden cases ask about (alias AP-1029)
PARTNER_ALIASES = {"AP-1029": STORY_PARTNER}


class Driver(StrEnum):
    """What the world planted for a partner. Evaluation only; no engine reads it."""

    CASHIER = "CASHIER_FRICTION"
    POACHING = "COMPETITIVE_POACHING"
    REBATE = "REBATE_DISPUTE"
    DORMANT = "DORMANT_DECAY"
    SEASONAL = "SEASONAL_DIP"  # hard negative: a holiday dip that recovers
    GROWING = "GROWING"
    STABLE = "STABLE"


CHURN_DRIVERS = frozenset({Driver.CASHIER, Driver.POACHING, Driver.REBATE, Driver.DORMANT})


class Tier(StrEnum):
    SUPER = "TIER_1_SUPER"
    MASTER = "TIER_2_MASTER"
    AFFILIATE = "TIER_3_AFFILIATE"


@dataclass(frozen=True)
class NamedPartner:
    partner_id: str
    name: str
    tier: Tier
    region: str  # the coarse region the cohort test groups by
    market: str  # what the screen shows
    cohort: str
    driver: Driver


NAMED: tuple[NamedPartner, ...] = (
    NamedPartner("PTR-882", "Alpha FX LatAm Master", Tier.SUPER, "LatAm", "LatAm (Colombia)", "LatAm P2P Cashier", Driver.CASHIER),
    NamedPartner("PTR-419", "Iberia Prime Affiliates", Tier.MASTER, "LatAm", "LatAm / Iberia Desk", "LatAm P2P Cashier", Driver.CASHIER),
    NamedPartner("PTR-104", "Nordic Quant Capital", Tier.SUPER, "EU", "Nordics / EU", "Nordic Institutional EA", Driver.STABLE),
    NamedPartner("PTR-551", "APAC Retail Signals Hub", Tier.AFFILIATE, "SEA", "SEA / Sub-IB Network", "SEA Retail", Driver.POACHING),
    NamedPartner("PTR-723", "Saigon FX Syndicate", Tier.MASTER, "SEA", "SEA (Vietnam)", "SEA Tier-1 Introducers", Driver.POACHING),
    NamedPartner("PTR-302", "Jakarta Algorithmic Traders", Tier.SUPER, "SEA", "SEA (Indonesia)", "SEA Institutional", Driver.GROWING),
    NamedPartner("PTR-618", "Bangkok Crypto Arbitrage", Tier.MASTER, "SEA", "SEA (Thailand)", "SEA P2P Gateway", Driver.CASHIER),
    NamedPartner("PTR-910", "Manila Prime Introducers", Tier.AFFILIATE, "SEA", "SEA (Philippines)", "SEA Retail", Driver.STABLE),
    NamedPartner("PTR-215", "London FX Proprietary Network", Tier.SUPER, "EU", "UK / London", "London Pro Desk", Driver.STABLE),
    NamedPartner("PTR-442", "Frankfurt Algo Desk", Tier.SUPER, "EU", "Germany / Frankfurt", "DAX Institutional", Driver.STABLE),
    NamedPartner("PTR-339", "Medellin P2P Payment Ring", Tier.MASTER, "LatAm", "LatAm (Colombia)", "LatAm P2P Cashier", Driver.CASHIER),
    NamedPartner("PTR-774", "Sao Paulo Futures Guild", Tier.SUPER, "LatAm", "LatAm (Brazil)", "Brazil PIX Network", Driver.SEASONAL),
    NamedPartner("PTR-128", "Mexico City CopyTrading IB", Tier.MASTER, "LatAm", "LatAm (Mexico)", "LatAm Retail Masters", Driver.REBATE),
    NamedPartner("PTR-805", "Lima Digital Assets Network", Tier.AFFILIATE, "LatAm", "LatAm (Peru)", "Andean Affiliates", Driver.DORMANT),
    NamedPartner("PTR-663", "Madrid Multi-Asset Partners", Tier.MASTER, "EU", "Spain / Europe", "Iberia Prime", Driver.STABLE),
    NamedPartner("PTR-991", "Limassol Institutional Liquidity", Tier.SUPER, "EU", "Cyprus / EU", "EU B2B Liquidity", Driver.GROWING),
    NamedPartner("PTR-520", "Kuala Lumpur Synthetics Hub", Tier.MASTER, "SEA", "SEA (Malaysia)", "SEA Synthetics", Driver.REBATE),
    NamedPartner("PTR-284", "Warsaw Quant Laboratory", Tier.AFFILIATE, "EU", "Poland / CEE", "CEE Quant", Driver.STABLE),
    NamedPartner("PTR-607", "Santiago Derivatives Desk", Tier.MASTER, "LatAm", "LatAm (Chile)", "Andean Affiliates", Driver.POACHING),
    NamedPartner("PTR-476", "Bogota Sub-Affiliate Cluster", Tier.AFFILIATE, "LatAm", "LatAm (Colombia)", "LatAm P2P Cashier", Driver.CASHIER),
    NamedPartner(AML_RING_PARTNER, "Singapore Retail Introducers", Tier.MASTER, "SEA", "SEA (Singapore)", "SEA Retail", Driver.STABLE),
)  # fmt: skip

REGIONS = ("LatAm", "SEA", "EU", "MENA", "Africa")
REGION_WEIGHTS = (0.26, 0.30, 0.20, 0.12, 0.12)
MARKETS = {
    "LatAm": ("Colombia", "Brazil", "Mexico", "Peru", "Chile"),
    "SEA": ("Malaysia", "Indonesia", "Vietnam", "Thailand", "Philippines"),
    "EU": ("Cyprus", "Poland", "Spain", "Germany", "UK"),
    "MENA": ("UAE", "Egypt", "Jordan", "Morocco"),
    "Africa": ("Nigeria", "Kenya", "South Africa", "Ghana"),
}
TIER_WEIGHTS = (0.15, 0.35, 0.50)
COMPETITORS = ("Competitor Alpha", "Competitor Beta", "Competitor Gamma")


@dataclass(frozen=True)
class PartnerWorldConfig:
    """Size and planted-driver shares. Counts exclude the named partners."""

    seed: int = DEFAULT_SEED
    n_partners: int = 240
    as_of: datetime = DEFAULT_AS_OF
    history_days: int = 70  # long enough to score at t-30 with a 28-day lookback
    churn_share: float = 0.12
    seasonal_share: float = 0.06
    growing_share: float = 0.15
    cohort_region: str = "SEA"  # a synchronized poaching wave the cohort test must find
    cohort_size: int = 14
    n_collusive_pairs: int = 6
    background_accounts: int = 400

    def fingerprint(self) -> str:
        return (
            f"{self.seed}-{self.n_partners}-{self.as_of:%Y%m%d%H%M}-{self.history_days}-"
            f"{self.churn_share}-{self.seasonal_share}-{self.growing_share}-{self.cohort_region}-"
            f"{self.cohort_size}-{self.n_collusive_pairs}-{self.background_accounts}"
        )
