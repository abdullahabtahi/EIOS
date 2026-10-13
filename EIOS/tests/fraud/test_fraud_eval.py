"""Eval-First Blocking Evaluation Gate: Pair Detector vs Naive Baseline (Constitution Principle VI).

Authoritative References:
- docs/models_and_evals.md §4
- specs/009-partner-fraud/research.md §6
- specs/009-partner-fraud/quickstart.md (Scenario 1)

Guarantees:
1. Multi-factor candidate-pruned pair detector beats naive threshold rule baseline by >= 0.15 PR-AUC.
2. False Positive Rate on hard-negative legitimate hedgers is strictly bounded (< 5.0%).
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import auc, precision_recall_curve

from eios.fraud.baseline import NaiveOppositeTradeBaseline
from eios.fraud.pair_detector import TimeBucketedPairDetector


def generate_sealed_eval_dataset(seed: int = 42) -> tuple[pd.DataFrame, dict[tuple[str, str], int]]:
    """Generate reproducible sealed holdout dataset with planted collusive pairs and hard negatives."""
    rng = np.random.default_rng(seed)
    base_ts = datetime(2026, 10, 1, 9, 0, 0)
    records = []
    ground_truth: dict[tuple[str, str], int] = {}
    trade_id = 1

    # 1. 10 Planted Collusive Opposite Pairs (True Positives, label = 1)
    for p_idx in range(10):
        acc_a = f"ACC-EV-OPP-A{p_idx:02d}"
        acc_b = f"ACC-EV-OPP-B{p_idx:02d}"
        part_a = f"P-FRAUD-A{p_idx:02d}"
        part_b = f"P-FRAUD-B{p_idx:02d}"
        pair_key = (min(acc_a, acc_b), max(acc_a, acc_b))
        ground_truth[pair_key] = 1

        for t_idx in range(15):
            t1 = base_ts + timedelta(minutes=10 * t_idx + p_idx * 60)
            # Tight delta: 1 to 6 seconds
            delta_s = rng.uniform(1.0, 6.0)
            t2 = t1 + timedelta(seconds=delta_s)
            lot = float(rng.choice([1.0, 2.0, 5.0, 10.0]))

            records.append(
                {
                    "trade_id": f"TRD-EV-{trade_id:06d}",
                    "account_id": acc_a,
                    "partner_id": part_a,
                    "symbol": "EURUSD",
                    "direction": "BUY",
                    "lots": lot,
                    "timestamp": t1,
                    "pnl_usd": 500.0,
                    "commission_usd": 25.0,
                }
            )
            trade_id += 1

            records.append(
                {
                    "trade_id": f"TRD-EV-{trade_id:06d}",
                    "account_id": acc_b,
                    "partner_id": part_b,
                    "symbol": "EURUSD",
                    "direction": "SELL",
                    "lots": lot,
                    "timestamp": t2,
                    "pnl_usd": -498.0,  # Zero-sum P&L
                    "commission_usd": 25.0,
                }
            )
            trade_id += 1

    # 2. 10 Hard-Negative Legitimate Hedgers (True Negatives, label = 0)
    # These execute opposite direction in same symbol, but with loose timing (15-45s)
    # and asymmetric sizes / P&L
    for h_idx in range(10):
        acc_h1 = f"ACC-EV-HEDGE-1{h_idx:02d}"
        acc_h2 = f"ACC-EV-HEDGE-2{h_idx:02d}"
        part_h1 = f"P-LEGIT-H1{h_idx:02d}"
        part_h2 = f"P-LEGIT-H2{h_idx:02d}"
        pair_key = (min(acc_h1, acc_h2), max(acc_h1, acc_h2))
        ground_truth[pair_key] = 0

        for t_idx in range(15):
            t1 = base_ts + timedelta(minutes=8 * t_idx + h_idx * 45)
            # Delta between 16 and 35 seconds (often triggers naive 30s rule!)
            delta_s = rng.uniform(16.0, 35.0)
            t2 = t1 + timedelta(seconds=delta_s)

            records.append(
                {
                    "trade_id": f"TRD-EV-{trade_id:06d}",
                    "account_id": acc_h1,
                    "partner_id": part_h1,
                    "symbol": "EURUSD",
                    "direction": "BUY" if t_idx % 2 == 0 else "SELL",
                    "lots": 1.0,
                    "timestamp": t1,
                    "pnl_usd": rng.uniform(-400.0, 600.0),
                    "commission_usd": 15.0,
                }
            )
            trade_id += 1

            records.append(
                {
                    "trade_id": f"TRD-EV-{trade_id:06d}",
                    "account_id": acc_h2,
                    "partner_id": part_h2,
                    "symbol": "EURUSD",
                    "direction": "SELL" if t_idx % 2 == 0 else "BUY",
                    "lots": 3.5,  # Asymmetric lot size
                    "timestamp": t2,
                    "pnl_usd": rng.uniform(-800.0, 900.0),  # Not zero-sum
                    "commission_usd": 30.0,
                }
            )
            trade_id += 1

    # 3. 20 Background Retail Accounts (True Negatives, label = 0)
    for b_idx in range(20):
        acc = f"ACC-EV-RETAIL-{b_idx:02d}"
        part = f"P-RET-{b_idx % 4:02d}"
        for t_idx in range(10):
            t = base_ts + timedelta(minutes=int(rng.integers(1, 200)))
            records.append(
                {
                    "trade_id": f"TRD-EV-{trade_id:06d}",
                    "account_id": acc,
                    "partner_id": part,
                    "symbol": "EURUSD" if t_idx % 2 == 0 else "GBPUSD",
                    "direction": rng.choice(["BUY", "SELL"]),
                    "lots": rng.uniform(0.1, 2.0),
                    "timestamp": t,
                    "pnl_usd": rng.uniform(-100.0, 100.0),
                    "commission_usd": 5.0,
                }
            )
            trade_id += 1

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df, ground_truth


def compute_pr_auc(y_true: list[int], y_scores: list[float]) -> float:
    """Compute PR-AUC score handling edge cases safely."""
    if sum(y_true) == 0:
        return 0.0
    precision, recall, _ = precision_recall_curve(y_true, y_scores)
    return float(auc(recall, precision))


def test_baseline_and_pair_detector_eval_gate() -> None:
    """Constitution Principle VI: Pair detector must beat naive baseline by >= 0.15 PR-AUC."""
    trade_df, ground_truth = generate_sealed_eval_dataset(seed=20261007)

    # 1. Run Pre-Registered Naive Baseline
    naive_detector = NaiveOppositeTradeBaseline(max_time_delta_sec=30.0)
    naive_preds = naive_detector.evaluate_trades(trade_df)

    # Aggregate naive predictions per candidate pair
    pair_naive_scores: dict[tuple[str, str], float] = {k: 0.0 for k in ground_truth}
    for p in naive_preds:
        pair_key = (min(p.account_a, p.account_b), max(p.account_a, p.account_b))
        if pair_key in pair_naive_scores:
            pair_naive_scores[pair_key] = max(pair_naive_scores[pair_key], p.score)

    y_true = [ground_truth[k] for k in ground_truth]
    y_naive = [pair_naive_scores[k] for k in ground_truth]
    naive_pr_auc = compute_pr_auc(y_true, y_naive)

    # 2. Run Candidate-Pruned Multi-Factor Pair Detector
    ml_detector = TimeBucketedPairDetector(
        bucket_window_sec=30.0,
        tau_timing_sec=5.0,
        min_co_occurrences=3,
    )
    detected_pairs = ml_detector.detect_pairs(trade_df)

    pair_ml_scores: dict[tuple[str, str], float] = {k: 0.0 for k in ground_truth}
    for pair in detected_pairs:
        pair_key = (min(pair.account_a, pair.account_b), max(pair.account_a, pair.account_b))
        if pair_key in pair_ml_scores:
            pair_ml_scores[pair_key] = pair.collusion_confidence

    y_ml = [pair_ml_scores[k] for k in ground_truth]
    ml_pr_auc = compute_pr_auc(y_true, y_ml)

    delta_pr_auc = ml_pr_auc - naive_pr_auc

    print(f"\n[EVAL GATE RESULTS] Naive Baseline PR-AUC: {naive_pr_auc:.4f}")
    print(f"[EVAL GATE RESULTS] ML Pair Detector PR-AUC: {ml_pr_auc:.4f}")
    print(f"[EVAL GATE RESULTS] Delta PR-AUC: {delta_pr_auc:.4f}")

    # Assertion 1: Must beat naive baseline by at least 0.15 PR-AUC
    assert delta_pr_auc >= 0.15, (
        f"Constitution Principle VI failure: Delta PR-AUC {delta_pr_auc:.4f} is less than required 0.15"
    )

    # Assertion 2: False Positive Rate on hard-negative legitimate hedgers must be < 5.0%
    hard_negative_keys = [k for k, label in ground_truth.items() if label == 0]
    hard_neg_false_positives = sum(
        1 for k in hard_negative_keys if pair_ml_scores.get(k, 0.0) >= 0.60
    )
    fpr_hedgers = hard_neg_false_positives / len(hard_negative_keys)
    print(f"[EVAL GATE RESULTS] Hard Negative FPR: {fpr_hedgers:.4%}")

    assert fpr_hedgers < 0.05, (
        f"False Positive Rate on legitimate hedgers ({fpr_hedgers:.4%}) exceeds 5%"
    )
