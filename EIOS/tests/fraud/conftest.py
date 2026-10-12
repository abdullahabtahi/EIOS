"""Test fixtures and synthetic generators for Partner Fraud Sentinel tests.

Provides deterministic seeded synthetic data:
- Planted opposite and mirror trading pairs
- Hard negative legitimate hedger accounts
- 3-tier sub-affiliate referral networks
- Bonus harvesting client lifecycles
- Recycled identity tokens (tok_id_cluster_<hex16>)
- Bot and traffic conversion anomalies
"""

from datetime import datetime, timedelta
import pandas as pd
import pytest


@pytest.fixture
def base_timestamp() -> datetime:
    return datetime(2026, 10, 1, 10, 0, 0)


@pytest.fixture
def synthetic_trade_log(base_timestamp: datetime) -> pd.DataFrame:
    """Generate trade log with planted opposite pairs, mirror pairs, and legitimate hedgers."""
    records = []
    trade_id_seq = 1

    # 1. Planted Opposite Trading Pair: Account A (Partner P-OPP-1) & Account B (Partner P-OPP-2)
    # 20 correlated trades within 3-10s window on EURUSD, inverse direction, near zero-sum P&L
    for i in range(20):
        t1 = base_timestamp + timedelta(minutes=15 * i)
        t2 = t1 + timedelta(seconds=4)

        # Account A buys 5.0 lots
        records.append({
            "trade_id": f"TRD-{trade_id_seq:05d}",
            "account_id": "ACC-OPP-A1",
            "partner_id": "P-OPP-1",
            "symbol": "EURUSD",
            "direction": "BUY",
            "lots": 5.0,
            "timestamp": t1,
            "pnl_usd": 1250.0 + (i % 3) * 10,
            "commission_usd": 50.0,
        })
        trade_id_seq += 1

        # Account B sells 5.0 lots (opposite)
        records.append({
            "trade_id": f"TRD-{trade_id_seq:05d}",
            "account_id": "ACC-OPP-B1",
            "partner_id": "P-OPP-2",
            "symbol": "EURUSD",
            "direction": "SELL",
            "lots": 5.0,
            "timestamp": t2,
            "pnl_usd": -1245.0 - (i % 3) * 10,
            "commission_usd": 50.0,
        })
        trade_id_seq += 1

    # 2. Planted Mirror Trading Pair: Account C (Partner P-MIRR-1) & Account D (Partner P-MIRR-2)
    for i in range(15):
        t1 = base_timestamp + timedelta(minutes=20 * i + 5)
        t2 = t1 + timedelta(seconds=2)

        records.append({
            "trade_id": f"TRD-{trade_id_seq:05d}",
            "account_id": "ACC-MIRR-C1",
            "partner_id": "P-MIRR-1",
            "symbol": "GBPUSD",
            "direction": "BUY",
            "lots": 2.5,
            "timestamp": t1,
            "pnl_usd": 320.0,
            "commission_usd": 25.0,
        })
        trade_id_seq += 1

        records.append({
            "trade_id": f"TRD-{trade_id_seq:05d}",
            "account_id": "ACC-MIRR-D1",
            "partner_id": "P-MIRR-2",
            "symbol": "GBPUSD",
            "direction": "BUY",
            "lots": 2.5,
            "timestamp": t2,
            "pnl_usd": 315.0,
            "commission_usd": 25.0,
        })
        trade_id_seq += 1

    # 3. Hard-Negative Legitimate Hedgers: Account H1 (Partner P-HEDGE-1) & Account H2 (Partner P-HEDGE-2)
    # Trade same symbols occasionally opposite, but with wide execution windows (60s - 300s),
    # asymmetrical lot sizes, and realistic non-zero combined P&L
    for i in range(25):
        t1 = base_timestamp + timedelta(minutes=10 * i + 2)
        # Random non-synchronized timing
        t2 = t1 + timedelta(seconds=75 + (i * 13 % 180))

        records.append({
            "trade_id": f"TRD-{trade_id_seq:05d}",
            "account_id": "ACC-HEDGE-1",
            "partner_id": "P-HEDGE-1",
            "symbol": "EURUSD",
            "direction": "BUY" if i % 2 == 0 else "SELL",
            "lots": 1.0 + (i % 4) * 0.5,
            "timestamp": t1,
            "pnl_usd": (i * 35.0) - 200.0,
            "commission_usd": 15.0,
        })
        trade_id_seq += 1

        records.append({
            "trade_id": f"TRD-{trade_id_seq:05d}",
            "account_id": "ACC-HEDGE-2",
            "partner_id": "P-HEDGE-2",
            "symbol": "EURUSD",
            "direction": "SELL" if i % 3 == 0 else "BUY",
            "lots": 4.0,
            "timestamp": t2,
            "pnl_usd": (-i * 50.0) + 120.0,
            "commission_usd": 40.0,
        })
        trade_id_seq += 1

    # 4. Background Uncorrelated Retail Traders: 10 accounts under random partners
    for i in range(50):
        t = base_timestamp + timedelta(minutes=7 * i)
        records.append({
            "trade_id": f"TRD-{trade_id_seq:05d}",
            "account_id": f"ACC-RETAIL-{i % 10:02d}",
            "partner_id": f"P-RETAIL-{i % 5:02d}",
            "symbol": "USDJPY" if i % 2 == 0 else "EURUSD",
            "direction": "BUY" if i % 3 != 0 else "SELL",
            "lots": 0.5,
            "timestamp": t,
            "pnl_usd": (i % 7) * 20.0 - 50.0,
            "commission_usd": 5.0,
        })
        trade_id_seq += 1

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@pytest.fixture
def synthetic_referral_tree() -> list[dict]:
    """Hierarchical partner network with 3 tiers and high-degree legitimate hub."""
    return [
        # Root Master Partner with illicit sub-network
        {"partner_id": "P-MASTER-01", "parent_partner_id": None, "tier_level": 1, "direct_referred_clients": 5, "direct_commission_usd": 1500.0, "sub_affiliate_count": 2, "is_root_master": True},
        {"partner_id": "P-SUB-01-A", "parent_partner_id": "P-MASTER-01", "tier_level": 2, "direct_referred_clients": 12, "direct_commission_usd": 4200.0, "sub_affiliate_count": 2, "is_root_master": False},
        {"partner_id": "P-SUB-01-B", "parent_partner_id": "P-MASTER-01", "tier_level": 2, "direct_referred_clients": 8, "direct_commission_usd": 2800.0, "sub_affiliate_count": 0, "is_root_master": False},
        {"partner_id": "P-LEAF-01-A1", "parent_partner_id": "P-SUB-01-A", "tier_level": 3, "direct_referred_clients": 45, "direct_commission_usd": 12500.0, "sub_affiliate_count": 0, "is_root_master": False},
        {"partner_id": "P-LEAF-01-A2", "parent_partner_id": "P-SUB-01-A", "tier_level": 3, "direct_referred_clients": 30, "direct_commission_usd": 8900.0, "sub_affiliate_count": 0, "is_root_master": False},

        # High-degree legitimate introducing broker (hub suppression candidate)
        {"partner_id": "P-LEGIT-HUB", "parent_partner_id": None, "tier_level": 1, "direct_referred_clients": 250, "direct_commission_usd": 95000.0, "sub_affiliate_count": 80, "is_root_master": True},
    ]


@pytest.fixture
def synthetic_client_lifecycles() -> list[dict]:
    """Client lifecycle events with bonus abuse syndicates vs organic portfolios."""
    records = []
    # Partner P-ABUSE-100: 100 referred clients, 85 withdraw within 48h with <= 1 micro-trade
    for i in range(100):
        is_abuse = i < 85
        records.append({
            "client_id": f"CL-ABUSE-{i:03d}",
            "partner_id": "P-ABUSE-100",
            "deposit_usd": 100.0,
            "withdrawal_usd": 100.0 if is_abuse else 40.0,
            "deposit_to_withdrawal_hours": 36.0 if is_abuse else 450.0,
            "trade_count": 1 if is_abuse else 28,
            "volume_usd": 100.0 if is_abuse else 35000.0,
            "cpa_collected_usd": 200.0,
            "active_30d": not is_abuse,
        })

    # Partner P-ORGANIC-50: 50 organic clients with normal holding and activity
    for i in range(50):
        records.append({
            "client_id": f"CL-ORG-{i:03d}",
            "partner_id": "P-ORGANIC-50",
            "deposit_usd": 500.0 + (i * 20.0),
            "withdrawal_usd": 150.0 if i % 4 == 0 else 0.0,
            "deposit_to_withdrawal_hours": 600.0 if i % 4 == 0 else 0.0,
            "trade_count": 45,
            "volume_usd": 85000.0,
            "cpa_collected_usd": 200.0,
            "active_30d": True,
        })

    return records


@pytest.fixture
def synthetic_identity_clusters() -> list[dict]:
    """Identity clusters mapping tok_id_cluster_<hex16> across multiple affiliates."""
    return [
        # Syndicate 1: Recycled token across 4 partners
        {
            "identity_cluster_key": "tok_id_cluster_a1b2c3d4e5f60001",
            "linked_client_ids": ["CL-REC-01", "CL-REC-02", "CL-REC-03", "CL-REC-04"],
            "distinct_partner_ids": ["P-AFF-11", "P-AFF-12", "P-AFF-13", "P-AFF-14"],
            "total_promotions_harvested_usd": 3200.0,
            "first_seen": datetime(2026, 8, 1, 0, 0, 0),
            "last_seen": datetime(2026, 10, 2, 0, 0, 0),
            "syndicate_risk_score": 0.94,
        },
        # Legitimate single-partner cluster
        {
            "identity_cluster_key": "tok_id_cluster_0011223344556677",
            "linked_client_ids": ["CL-SOLO-01"],
            "distinct_partner_ids": ["P-AFF-99"],
            "total_promotions_harvested_usd": 100.0,
            "first_seen": datetime(2026, 9, 15, 0, 0, 0),
            "last_seen": datetime(2026, 9, 15, 0, 0, 0),
            "syndicate_risk_score": 0.05,
        },
    ]


@pytest.fixture
def synthetic_clickstream_funnels() -> list[dict]:
    """Marketing funnels: bot traffic vs organic cohorts."""
    return [
        # Bot affiliate: 10,000 clicks, 9,200 registrations, 8,900 FTDs (impossible ~90% conversion)
        {
            "partner_id": "P-BOT-TRAFFIC",
            "click_count": 10000,
            "registration_count": 9200,
            "ftd_count": 8900,
            "click_to_signup_rate": 0.92,
            "signup_to_deposit_rate": 0.967,
            "peer_cohort_mean_conversion": 0.045,
            "p_value": 0.00001,
            "bot_traffic_probability": 0.99,
            "anomaly_flag": True,
        },
        # Normal organic affiliate: 5,000 clicks, 220 signups, 45 FTDs (~0.9% conversion)
        {
            "partner_id": "P-NORMAL-MKT",
            "click_count": 5000,
            "registration_count": 220,
            "ftd_count": 45,
            "click_to_signup_rate": 0.044,
            "signup_to_deposit_rate": 0.204,
            "peer_cohort_mean_conversion": 0.045,
            "p_value": 0.48,
            "bot_traffic_probability": 0.03,
            "anomaly_flag": False,
        },
    ]
