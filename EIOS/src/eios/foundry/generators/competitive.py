"""Competitor benchmark intelligence generator using generic aliases (FR-044, SC-003)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from eios.foundry.contracts import CompetitorEventRecord, ContractValidator
from eios.foundry.rng import RNGManager

GENERIC_ALIASES = [
    "Competitor Alpha",
    "Competitor Beta",
    "Competitor Gamma",
    "Competitor Delta",
    "Competitor Epsilon",
    "Competitor Zeta",
]

EVENT_TYPES = ["PAYOUT_INCREASE", "SPREAD_CUT", "PROMO_CAMPAIGN", "ACQUISITION"]


class CompetitiveDataGenerator:
    """Generates competitor event intelligence strictly using generic aliases."""

    def __init__(self, rng: RNGManager) -> None:
        self.rng = rng
        self._gen = rng.get_generator("competitive_intel")
        self._validator = ContractValidator(CompetitorEventRecord)

    def generate_events(self, count: int = 30) -> list[dict[str, Any]]:
        """Generates validated competitor events."""
        records: list[dict[str, Any]] = []
        base_dt = datetime(2025, 2, 1, 0, 0, 0, tzinfo=UTC)

        for i in range(count):
            dt = base_dt + timedelta(days=i * 2, hours=int(self._gen.integers(1, 12)))
            alias = GENERIC_ALIASES[i % len(GENERIC_ALIASES)]
            event_type = EVENT_TYPES[i % len(EVENT_TYPES)]
            delta_val = float(self._gen.uniform(0.02, 0.15))

            records.append(
                {
                    "event_id": f"CMP-{i + 1:06d}",
                    "competitor_alias": alias,
                    "event_type": event_type,
                    "delta_value": delta_val,
                    "timestamp": dt.isoformat(),
                }
            )

        self._validator.validate_batch(records)
        return records
