"""Eval-First Blocking Evaluation Gate: Supervised Triage Scorer vs Naive Baseline (Constitution Principle VI).

Authoritative References:
- docs/models_and_evals.md §2
- specs/010-client-aml/research.md §7
- specs/010-client-aml/quickstart.md (Scenario 1)

Guarantees:
1. Supervised alert triage scorer beats pre-registered naive threshold rule baseline by >= 0.15 PR-AUC on sealed seeds.
2. False Positive Rate on hard-negative legitimate high-volume retail traders achieves >= 30% relative reduction.
"""

from datetime import datetime, timedelta
import numpy as np
import pytest
from sklearn.metrics import precision_recall_curve, auc

from eios.aml.baseline import NaiveThresholdBaseline
from eios.aml.models import AMLAlert, AMLPriorityTier, AMLTriggerType, AMLTypology
from eios.aml.triage_scorer import AlertTriageScorer


def generate_sealed_aml_dataset(seed: int = 100) -> tuple[list[AMLAlert], dict[str, int], set[str]]:
    """Generate reproducible sealed holdout dataset with planted laundering and hard negatives."""
    rng = np.random.default_rng(seed)
    base_ts = datetime(2026, 10, 1, 8, 0, 0)
    alerts: list[AMLAlert] = []
    ground_truth: dict[str, int] = {}
    hard_negative_ids: set[str] = set()

    # 1. 30 Planted True Positives (label = 1)
    for i in range(30):
        aid = f"ALT-SEALED-TP-{i:03d}"
        cid = f"C-SEALED-TP-{i:03d}"
        ground_truth[aid] = 1

        is_rt = (i % 2 == 0)
        alerts.append(
            AMLAlert(
                alert_id=aid,
                client_id=cid,
                trigger_type=AMLTriggerType.ROUND_TRIP_SEQUENCE if is_rt else AMLTriggerType.MULE_RING_CLUSTER,
                risk_score=float(rng.uniform(0.85, 0.98)),
                priority_tier=AMLPriorityTier.CRITICAL,
                typology=AMLTypology.MICRO_PNL_WASH if is_rt else AMLTypology.MULE_SYNDICATE,
                amount_usd=float(rng.uniform(500.0, 9500.0)),
                triggered_at=base_ts + timedelta(minutes=15 * i),
                is_triage_top50=True,
                attributes={
                    "is_planted_tp": True,
                    "hours_since_kyc": float(rng.uniform(1.0, 48.0)),
                    "peer_z_score": float(rng.uniform(3.0, 6.0)),
                    "deposit_withdrawal_ratio": float(rng.uniform(0.95, 1.05)),
                    "mule_cluster_size": int(rng.integers(6, 18)) if not is_rt else 1,
                    "market_risk_pct": float(rng.uniform(0.0001, 0.008)),
                    "withdrawal_count_24h": int(rng.integers(1, 3)),
                    "deposit_withdrawal_gap_mins": float(rng.uniform(5.0, 45.0)),
                },
            )
        )

    # 2. 30 Hard Negatives (Legitimate High-Volume Traders, label = 0)
    for i in range(30):
        aid = f"ALT-SEALED-HN-{i:03d}"
        cid = f"C-SEALED-HN-{i:03d}"
        ground_truth[aid] = 0
        hard_negative_ids.add(aid)

        alerts.append(
            AMLAlert(
                alert_id=aid,
                client_id=cid,
                trigger_type=AMLTriggerType.THRESHOLD_RULE,
                risk_score=float(rng.uniform(0.40, 0.65)),
                priority_tier=AMLPriorityTier.MEDIUM,
                typology=AMLTypology.NONE,
                amount_usd=float(rng.uniform(12000.0, 45000.0)),  # Trips naive amount threshold!
                triggered_at=base_ts + timedelta(minutes=20 * i),
                is_triage_top50=False,
                attributes={
                    "is_hard_negative": True,
                    "hours_since_kyc": float(rng.uniform(500.0, 2000.0)),
                    "peer_z_score": float(rng.uniform(0.5, 2.0)),
                    "deposit_withdrawal_ratio": float(rng.uniform(0.15, 0.50)),
                    "mule_cluster_size": 1,
                    "market_risk_pct": float(rng.uniform(0.10, 0.40)),
                    "withdrawal_count_24h": int(rng.integers(4, 7)),  # Trips velocity threshold!
                    "deposit_withdrawal_gap_mins": float(rng.uniform(120.0, 600.0)),
                },
            )
        )

    # 3. 440 Ambient Rule Noise Alerts (label = 0)
    for i in range(440):
        aid = f"ALT-SEALED-NOISE-{i:04d}"
        cid = f"C-SEALED-NOISE-{i:04d}"
        ground_truth[aid] = 0

        alerts.append(
            AMLAlert(
                alert_id=aid,
                client_id=cid,
                trigger_type=AMLTriggerType.THRESHOLD_RULE,
                risk_score=float(rng.uniform(0.10, 0.35)),
                priority_tier=AMLPriorityTier.LOW,
                typology=AMLTypology.NONE,
                amount_usd=float(rng.uniform(150.0, 8500.0)),
                triggered_at=base_ts + timedelta(minutes=5 * i),
                is_triage_top50=False,
                attributes={
                    "is_noise": True,
                    "hours_since_kyc": float(rng.uniform(100.0, 3000.0)),
                    "peer_z_score": float(rng.uniform(-1.0, 1.2)),
                    "deposit_withdrawal_ratio": float(rng.uniform(0.1, 0.7)),
                    "mule_cluster_size": 1,
                    "market_risk_pct": float(rng.uniform(0.05, 0.30)),
                    "withdrawal_count_24h": 1,
                    "deposit_withdrawal_gap_mins": float(rng.uniform(200.0, 2000.0)),
                },
            )
        )

    rng.shuffle(alerts)
    return alerts, ground_truth, hard_negative_ids


def test_triage_scorer_beats_naive_baseline_eval_gate() -> None:
    """Evaluate triage scorer against naive baseline on sealed seeds (Principle VI)."""
    alerts, ground_truth, hard_negative_ids = generate_sealed_aml_dataset(seed=2026)

    # 1. Run Naive Threshold Baseline
    naive_engine = NaiveThresholdBaseline()
    naive_results = naive_engine.evaluate_queue(alerts)
    naive_scores = [res.score for res in naive_results]

    # 2. Run Supervised Alert Triage Scorer
    triage_scorer = AlertTriageScorer()
    scored_alerts = triage_scorer.score_queue(alerts)
    scorer_scores = [a.risk_score for a in scored_alerts]

    y_true = np.array([ground_truth[a.alert_id] for a in alerts])
    y_naive = np.array(naive_scores)
    y_scorer = np.array(scorer_scores)

    # Calculate PR-AUC
    p_naive, r_naive, _ = precision_recall_curve(y_true, y_naive)
    pr_auc_naive = float(auc(r_naive, p_naive))

    p_scorer, r_scorer, _ = precision_recall_curve(y_true, y_scorer)
    pr_auc_scorer = float(auc(r_scorer, p_scorer))

    delta_pr_auc = pr_auc_scorer - pr_auc_naive

    print(f"\n--- EVALUATION GATE: Client AML Triage Scorer ---")
    print(f"Naive Baseline PR-AUC: {pr_auc_naive:.4f}")
    print(f"Supervised Scorer PR-AUC: {pr_auc_scorer:.4f}")
    print(f"PR-AUC Improvement Delta: +{delta_pr_auc:.4f} (Required: >= 0.1500)")

    # Assert Principle VI Gate
    assert delta_pr_auc >= 0.15, (
        f"Constitution Principle VI Violation: Scorer delta +{delta_pr_auc:.4f} < 0.1500"
    )

    # 3. Hard-Negative False Positive Rate comparison
    naive_hn_flags = [
        res.flagged for res in naive_results if res.alert_id in hard_negative_ids
    ]
    naive_hn_fpr = sum(naive_hn_flags) / len(naive_hn_flags)

    scorer_hn_flags = [
        a.risk_score >= 0.70 for a in scored_alerts if a.alert_id in hard_negative_ids
    ]
    scorer_hn_fpr = sum(scorer_hn_flags) / len(scorer_hn_flags)

    relative_fpr_reduction = (naive_hn_fpr - scorer_hn_fpr) / max(naive_hn_fpr, 0.001)

    print(f"Naive Hard-Negative FPR: {naive_hn_fpr:.2%}")
    print(f"Supervised Hard-Negative FPR: {scorer_hn_fpr:.2%}")
    print(f"Relative FPR Reduction: {relative_fpr_reduction:.2%} (Required: >= 30.0%)")

    assert relative_fpr_reduction >= 0.30, (
        f"Failed relative FPR reduction target: {relative_fpr_reduction:.2%} < 30.0%"
    )
    assert scorer_hn_fpr <= 0.10, f"Absolute Hard-Negative FPR too high: {scorer_hn_fpr:.2%}"
