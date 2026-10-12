"""Financial P&L and accounting telemetry generator (FR-043)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from eios.foundry.contracts import ContractValidator, DailyPnLRecord
from eios.foundry.rng import RNGManager
from eios.foundry.universe import GlobalEntityUniverse


class FinancialDataGenerator:
    """Generates daily P&L adhering strictly to enterprise accounting identities."""

    def __init__(self, universe: GlobalEntityUniverse, rng: RNGManager) -> None:
        self.universe = universe
        self.rng = rng
        self._gen = rng.get_generator("financial_pnl")
        self._validator = ContractValidator(DailyPnLRecord)

    def generate_daily_pnl(self, days: int = 30) -> List[Dict[str, Any]]:
        """Generates validated daily P&L entries with organic volume derivation."""
        records: List[Dict[str, Any]] = []
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        for d in range(days):
            date_str = (base_date + timedelta(days=d)).strftime("%Y-%m-%d")
            gross_vol = Decimal(f"{int(self._gen.integers(120_000, 250_000))}.00")
            net_spread = Decimal(f"{int(self._gen.integers(80_000, 110_000))}.00")
            partner_comm = Decimal(f"{int(self._gen.integers(25_000, 35_000))}.00")
            ops_cost = Decimal(f"{int(self._gen.integers(15_000, 20_000))}.00")

            net_ebitda = net_spread - partner_comm - ops_cost

            records.append(
                {
                    "date": date_str,
                    "gross_trading_revenue": gross_vol,
                    "net_spread_revenue": net_spread,
                    "partner_commission_expense": partner_comm,
                    "operational_infrastructure_cost": ops_cost,
                    "net_ebitda": net_ebitda,
                }
            )

        self._validator.validate_batch(records)
        return records
