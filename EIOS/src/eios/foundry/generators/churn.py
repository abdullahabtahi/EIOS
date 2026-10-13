"""Partner churn radar and engagement signals generator (FR-035 to FR-041)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from eios.foundry.contracts import ContractValidator, WeeklySignalRecord
from eios.foundry.rng import RNGManager
from eios.foundry.universe import GlobalEntityUniverse


class ChurnDataGenerator:
    """Generates weekly partner engagement signals, seasonal dips, and regional cohort shocks."""

    def __init__(self, universe: GlobalEntityUniverse, rng: RNGManager) -> None:
        self.universe = universe
        self.rng = rng
        self._gen = rng.get_generator("churn_radar")
        self._validator = ContractValidator(WeeklySignalRecord)

    def generate_weekly_signals(self, weeks: int = 8) -> list[dict[str, Any]]:
        """Generates validated weekly signals across 5 indicator families."""
        records: list[dict[str, Any]] = []
        base_date = datetime(2025, 1, 6, tzinfo=UTC)
        sig_counter = 0

        for _p_idx, partner in enumerate(self.universe.partners):
            for w in range(weeks):
                sig_counter += 1
                week_start = (base_date + timedelta(weeks=w)).strftime("%Y-%m-%d")
                active_traders = max(0, int(self._gen.integers(5, 50)))
                ftd = max(0, int(self._gen.integers(0, 10)))
                conv = float(self._gen.uniform(0.05, 0.45))
                logins = max(0, int(self._gen.integers(1, 20)))
                sentiment = float(self._gen.uniform(-0.5, 0.8))
                poaching = 1 if self._gen.uniform(0, 1) < 0.04 else 0

                records.append(
                    {
                        "signal_id": f"SIG-{sig_counter:08d}",
                        "partner_id": partner.partner_id,
                        "week_start_date": week_start,
                        "active_traders_count": active_traders,
                        "weekly_ftd_count": ftd,
                        "click_to_signup_conversion": conv,
                        "weekly_logins": logins,
                        "average_ticket_sentiment": sentiment,
                        "poaching_language_flags": poaching,
                    }
                )

        self._validator.validate_batch(records)
        return records

    def get_seasonal_dip_partners(self) -> list[dict[str, Any]]:
        """Returns ~8% of partners who experienced a benign 30-day dip and recovered."""
        target_count = max(1, int(len(self.universe.partners) * 0.08))
        dips: list[dict[str, Any]] = []
        for i in range(target_count):
            partner = self.universe.partners[i]
            dips.append(
                {
                    "partner_id": partner.partner_id,
                    "dip_start_date": "2025-06-01",
                    "recovery_days": 30,
                    "is_recovered": True,
                    "reason": "SUMMER_SEASONALITY",
                }
            )
        return dips

    def get_regional_cohort_shock(self) -> dict[str, Any]:
        """Returns regional cohort disengagement event with 14-day lag."""
        latam_partners = [p.partner_id for p in self.universe.partners[:8]]
        return {
            "region": "LATAM",
            "event": "REGULATORY_LEVERAGE_CAP",
            "lag_days": 14,
            "affected_partners": latam_partners,
        }
