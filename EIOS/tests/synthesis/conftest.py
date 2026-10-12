from datetime import UTC, datetime

import numpy as np
import pytest

from eios.contracts.base import DataProductEnum
from eios.ingestion.hot_state import HotStateEngine


@pytest.fixture
def rng():
    """Deterministic PRNG for reproducible synthesis test suites."""
    return np.random.default_rng(seed=42)


@pytest.fixture
def synthetic_timeseries_data(rng):
    """Generate 90-day synthetic multi-domain metric history with known structural equations.

    DAG Ground Truth:
      competitor_payout_rate (exogenous)
      -> partner_churn_rate (beta = +0.45)
      -> ftd_count_28d (beta = -340.0)
      -> net_deposit_volume_usd (beta = +45.0)

    Planted Placebo:
      avg_spread_pip (independent, true effect on partner_churn_rate = 0.0)
    """
    n_days = 90
    dates = [f"2026-07-0{i + 1}" if i < 9 else f"2026-07-{i + 1}" for i in range(n_days)]

    # Exogenous competitor payout rate: baseline 0.35 with shocks
    payout_base = 0.35 + 0.05 * np.sin(np.linspace(0, 4 * np.pi, n_days))
    competitor_payout = payout_base + rng.normal(0, 0.01, n_days)

    # Endogenous partner churn: linear response to competitor payout
    partner_churn = 0.05 + 0.45 * competitor_payout + rng.normal(0, 0.005, n_days)

    # Endogenous FTD count: negative response to partner churn
    ftd_count = 1500.0 - 340.0 * partner_churn + rng.normal(0, 10.0, n_days)

    # Endogenous net deposit volume: positive response to FTDs
    net_deposit = 10000.0 + 45.0 * ftd_count + rng.normal(0, 250.0, n_days)

    # Planted placebo: independent spread
    avg_spread = 1.2 + 0.2 * rng.standard_normal(n_days)

    return {
        "dates": dates,
        "competitor_payout_rate": competitor_payout,
        "partner_churn_rate": partner_churn,
        "ftd_count_28d": ftd_count,
        "net_deposit_volume_usd": net_deposit,
        "avg_spread_pip": avg_spread,
    }


@pytest.fixture
def seeded_hot_state():
    """Provide initialized HotStateEngine populated with deterministic records for synthesis tests."""
    engine = HotStateEngine(db_path=":memory:")

    # Seed client_360
    for i in range(1, 21):
        engine.insert_event(
            DataProductEnum.CLIENT_360,
            {
                "client_id": f"C-{1000 + i}",
                "tax_id": f"TAX-{i}",
                "full_name": f"Trader {i}",
                "email": f"trader{i}@example.com",
                "phone": f"+1555000{i:04d}",
                "dob": "1990-01-01",
                "country": "CYP",
                "kyc_status": "APPROVED",
                "kyc_approved_at": datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
                "partner_id": f"P-{100 + (i % 3)}",
                "declared_monthly_income": 5000.0,
                "lifetime_value": 1500.0 * i,
                "segment": "VIP" if i > 15 else "STANDARD",
            },
        )

    # Seed partner_360
    for p in range(1, 4):
        engine.insert_event(
            DataProductEnum.PARTNER_360,
            {
                "partner_id": f"P-{100 + p}",
                "tier": "TIER_1" if p == 1 else "TIER_2",
                "region": "LATAM" if p == 1 else "EMEA",
                "tenure_months": 24 * p,
                "value_at_risk": 50000.0 * p,
                "manager_id": f"MGR-{p}",
                "status": "ACTIVE",
            },
        )

    # Seed transactions_aml
    for i in range(1, 31):
        is_deposit = i % 3 != 0
        engine.insert_event(
            DataProductEnum.TRANSACTIONS_AML,
            {
                "txn_id": f"TXN-{i}",
                "client_id": f"C-{1000 + (i % 10) + 1}",
                "txn_type": "deposit" if is_deposit else "withdrawal",
                "amount": 250.0 * i,
                "currency": "USD",
                "payment_method_id": f"PM-{(i % 4) + 1}",
                "payment_agent_id": None,
                "timestamp": datetime.now(UTC),
                "is_first_deposit": (i <= 10 and is_deposit),
                "status": "SETTLED",
            },
        )

    # Seed trading_activity
    for t in range(1, 11):
        engine.insert_event(
            DataProductEnum.TRADING_ACTIVITY,
            {
                "trade_id": f"TRD-{t}",
                "client_id": f"C-{1000 + t}",
                "symbol": "EURUSD",
                "side": "BUY",
                "volume": 1.5,
                "open_price": 1.0850,
                "close_price": 1.0860,
                "open_ts": datetime.now(UTC),
                "close_ts": datetime.now(UTC),
                "profit_loss": 150.0,
            },
        )

    # Seed competitor_benchmarks
    engine.insert_event(
        DataProductEnum.COMPETITOR_BENCHMARKS,
        {
            "competitor": "BrokerX",
            "date": "2026-10-06",
            "region": "GLOBAL",
            "payout_rate": 0.40,
            "spread_pips": 1.25,
            "promo_event": "FALL_FEE_WAIVER",
        },
    )

    yield engine
    engine.close()
