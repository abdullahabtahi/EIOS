"""Tests for financial P&L generation and accounting identity ties (FR-043, SC-002)."""

from eios.foundry.contracts import ContractValidator, DailyPnLRecord
from eios.foundry.generators.financial import FinancialDataGenerator
from eios.foundry.rng import DeterministicRNG
from eios.foundry.universe import GlobalEntityUniverse


def test_financial_pnl_identities_and_contracts():
    """Confirms DailyPnLRecord passes schema and adheres to accounting identities."""
    rng = DeterministicRNG(master_seed=42)
    universe = GlobalEntityUniverse(rng=rng, client_count=100)
    fin_gen = FinancialDataGenerator(universe=universe, rng=rng)

    pnl_records = fin_gen.generate_daily_pnl(days=30)
    assert len(pnl_records) == 30

    validator = ContractValidator(DailyPnLRecord)
    validated = validator.validate_batch(pnl_records)
    assert len(validated) == 30

    for rec in validated:
        # Accounting identity:
        # net_ebitda = net_spread_revenue - partner_commission_expense - operational_infrastructure_cost
        expected_ebitda = (
            rec.net_spread_revenue
            - rec.partner_commission_expense
            - rec.operational_infrastructure_cost
        )
        assert rec.net_ebitda == expected_ebitda
        assert rec.gross_trading_revenue >= rec.net_spread_revenue
