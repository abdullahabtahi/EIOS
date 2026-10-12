#!/usr/bin/env python3
"""Runnable Batch Script for Partner Fraud Sentinel Pipeline (T044).

Usage:
    python scripts/run_partner_fraud_pipeline.py --as-of 2026-10-07 --seed 42
"""

import argparse
from datetime import datetime, timedelta
import pandas as pd

from eios.fraud.pipeline import PartnerFraudPipeline
from eios.ingestion.hot_state import HotStateEngine


def generate_seed_data(seed: int = 42) -> tuple[pd.DataFrame, list[dict], list[dict], list[dict]]:
    base_ts = datetime(2026, 10, 1, 9, 0, 0)
    records = []
    trade_id = 1

    # 1. Opposite Trading Pairs
    for i in range(25):
        t1 = base_ts + timedelta(minutes=10 * i)
        t2 = t1 + timedelta(seconds=4)
        records.append({
            "trade_id": f"TRD-{trade_id:05d}",
            "account_id": "ACC-OPP-A1",
            "partner_id": "P-OPP-1",
            "symbol": "EURUSD",
            "direction": "BUY",
            "lots": 5.0,
            "timestamp": t1,
            "pnl_usd": 1500.0,
            "commission_usd": 50.0,
        })
        trade_id += 1
        records.append({
            "trade_id": f"TRD-{trade_id:05d}",
            "account_id": "ACC-OPP-B1",
            "partner_id": "P-OPP-2",
            "symbol": "EURUSD",
            "direction": "SELL",
            "lots": 5.0,
            "timestamp": t2,
            "pnl_usd": -1495.0,
            "commission_usd": 50.0,
        })
        trade_id += 1

    trade_df = pd.DataFrame(records)

    # 2. 3-tier tree records
    tree_records = [
        {"partner_id": "P-MASTER-01", "parent_partner_id": None, "tier_level": 1, "direct_referred_clients": 5, "direct_commission_usd": 1500.0, "sub_affiliate_count": 2, "is_root_master": True},
        {"partner_id": "P-SUB-01-A", "parent_partner_id": "P-MASTER-01", "tier_level": 2, "direct_referred_clients": 12, "direct_commission_usd": 4200.0, "sub_affiliate_count": 1, "is_root_master": False},
        {"partner_id": "P-OPP-1", "parent_partner_id": "P-SUB-01-A", "tier_level": 3, "direct_referred_clients": 45, "direct_commission_usd": 12500.0, "sub_affiliate_count": 0, "is_root_master": False},
        {"partner_id": "P-OPP-2", "parent_partner_id": None, "tier_level": 1, "direct_referred_clients": 30, "direct_commission_usd": 8900.0, "sub_affiliate_count": 0, "is_root_master": True},
    ]

    # 3. Client lifecycle events
    client_records = [
        {"client_id": f"CL-AB-{i}", "partner_id": "P-OPP-1", "deposit_usd": 100.0, "withdrawal_usd": 100.0, "deposit_to_withdrawal_hours": 24.0, "trade_count": 1, "volume_usd": 50.0, "cpa_collected_usd": 200.0, "active_30d": False}
        for i in range(40)
    ]

    # 4. Marketing funnels
    funnel_records = [
        {"partner_id": "P-OPP-1", "click_count": 500, "registration_count": 450, "ftd_count": 400, "click_to_signup_rate": 0.90, "signup_to_deposit_rate": 0.88, "p_value": 0.0001, "bot_traffic_probability": 0.95, "anomaly_flag": True}
    ]

    return trade_df, tree_records, client_records, funnel_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Run batch partner fraud detection pipeline.")
    parser.add_argument("--as-of", default="2026-10-07", help="As-of evaluation date")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    print(f"Initializing Partner Fraud Sentinel pipeline (as_of={args.as_of}, seed={args.seed})...")
    hot_state = HotStateEngine()
    pipeline = PartnerFraudPipeline(hot_state=hot_state)

    trade_df, tree_records, client_records, funnel_records = generate_seed_data(seed=args.seed)

    results = pipeline.run_pipeline(
        trade_df=trade_df,
        tree_records=tree_records,
        client_records=client_records,
        funnel_records=funnel_records,
    )

    print("\n--- Pipeline Execution Summary ---")
    print(f"Opposite/Mirror Trading Pairs Identified: {results['pairs_detected']}")
    print(f"Partners Scored and Persisted:             {results['scores_inserted']}")
    print(f"High-Severity Investigation Cases Opened:  {results['cases_inserted']}")

    cursor = hot_state.get_cursor()
    print("\n--- Sample Flagged Fraud Cases ---")
    rows = cursor.execute("SELECT case_id, partner_id, primary_typology, fraud_risk_score, total_exposure_usd, confidence_level FROM partner_fraud_cases LIMIT 5").fetchall()
    for r in rows:
        print(f"Case {r[0]}: Partner {r[1]} | Typology: {r[2]} | Risk: {r[3]:.2f} | Exposure: ${r[4]:,.2f} | Level: {r[5]}")

    print("\nBatch pipeline finished successfully.")


if __name__ == "__main__":
    main()
