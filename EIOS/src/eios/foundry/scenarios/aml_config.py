"""Configuration and fixed identities of the seeded AML world (spec 031 FR-001, FR-003).

The world is a pure function of this config: the same config always yields the same bytes. `as_of` is part of the
config so nothing reads the wall clock. The three story accounts keep the facts the golden cases and the
documentation already name.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

STORY_RING_HEAD = (
    "CR84920"  # income $500, 16 deposits of $500 in USDT, ring of 23, pending withdrawal
)
STORY_WASH = "CR91204"  # deposit, micro trades, withdrawal inside 12 minutes
STORY_DEVICE_RING = "CR73491"  # device ring of 8
STORY_IDS = (STORY_RING_HEAD, STORY_WASH, STORY_DEVICE_RING)

PAYMENT_AGENT_HUB = "PA-HUB-007"  # public payment gateway: degree above the RL-4 limit, suppressed
STORY_PARTNER = "PTR-401"

DEFAULT_SEED = 20261014
DEFAULT_AS_OF = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
WINDOW_DAYS = 30

COUNTRIES = ("SG", "MY", "ID", "TH", "VN", "AE", "IN", "BR", "CO", "NG")
COUNTRY_WEIGHTS = (0.12, 0.14, 0.16, 0.10, 0.10, 0.08, 0.12, 0.08, 0.05, 0.05)
EMPLOYMENT = ("Employed", "Self-Employed", "Student", "Retired", "Unemployed")
EMPLOYMENT_WEIGHTS = (0.52, 0.24, 0.10, 0.06, 0.08)
# Median declared monthly income (USD) by employment, scaled per country below.
INCOME_MEDIAN = {
    "Employed": 2400.0,
    "Self-Employed": 1900.0,
    "Student": 450.0,
    "Retired": 1100.0,
    "Unemployed": 380.0,
}
COUNTRY_INCOME_FACTOR = {
    "SG": 1.9,
    "AE": 1.8,
    "MY": 0.9,
    "TH": 0.8,
    "BR": 0.8,
    "CO": 0.7,
    "ID": 0.65,
    "VN": 0.6,
    "IN": 0.6,
    "NG": 0.55,
}


@dataclass(frozen=True)
class AmlWorldConfig:
    """Size and planted-typology counts. Counts exclude the three story accounts."""

    seed: int = DEFAULT_SEED
    n_clients: int = 6000
    as_of: datetime = DEFAULT_AS_OF
    window_days: int = WINDOW_DAYS
    partner_ids: tuple[str, ...] = ("PTR-882", "PTR-419", "PTR-104", "PTR-551", "PTR-723")
    n_wash: int = 16
    n_structuring: int = 12
    ring_sizes: tuple[int, ...] = (23, 8, 14, 11, 9, 7)  # the first two belong to the story
    n_cgnat_hubs: int = 3
    cgnat_degree: tuple[int, int] = (140, 320)
    n_hub_agent_clients: int = 142  # clients behind the public payment agent PA-HUB-007
    n_households: int = 45
    n_family_triplets: int = 6
    n_scalpers: int = 60
    n_wealthy: int = 40

    def fingerprint(self) -> str:
        """A stable key for caches: every field that changes the world."""
        return (
            f"{self.seed}-{self.n_clients}-{self.as_of:%Y%m%d%H%M}-{self.window_days}-"
            f"{self.n_wash}-{self.n_structuring}-{'.'.join(map(str, self.ring_sizes))}-"
            f"{self.n_cgnat_hubs}-{self.n_hub_agent_clients}-{self.n_households}-"
            f"{self.n_family_triplets}-{self.n_scalpers}-{self.n_wealthy}-{len(self.partner_ids)}"
        )
