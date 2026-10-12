"""Unit tests for Emerging Fraud Typology Discovery & Temporal Intelligence (T038 / US7).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US7)
"""

from datetime import datetime, timedelta
import pytest

from eios.fraud.emerging_patterns import EmergingPatternMiner, TemporalDriftAnalyzer


def test_emerging_pattern_miner_detects_unsupervised_cyclic_rebate_ring() -> None:
    # 4 partners in a cyclic rebate loop: A -> B -> C -> D -> A
    cyclic_edges = [
        {"from_partner": "P-LOOP-A", "to_partner": "P-LOOP-B", "rebate_pct": 25.0},
        {"from_partner": "P-LOOP-B", "to_partner": "P-LOOP-C", "rebate_pct": 25.0},
        {"from_partner": "P-LOOP-C", "to_partner": "P-LOOP-D", "rebate_pct": 25.0},
        {"from_partner": "P-LOOP-D", "to_partner": "P-LOOP-A", "rebate_pct": 25.0},
    ]

    miner = EmergingPatternMiner()
    anomalous_clusters = miner.mine_anomalous_subgraphs(cyclic_edges)

    assert len(anomalous_clusters) >= 1
    loop_cluster = anomalous_clusters[0]
    assert loop_cluster["typology_name"] == "CYCLIC_COMMISSION_REBATING"
    assert len(loop_cluster["participating_partners"]) == 4
    assert loop_cluster["structural_anomaly_score"] >= 0.85


def test_temporal_drift_analyzer_flags_abrupt_partner_behavioral_shift() -> None:
    # Partner history: 8 weeks of low volume / organic trading, then sudden 6x volume spike and 100% micro-trades in week 9-10
    weekly_history = []
    base_date = datetime(2026, 8, 1)
    for w in range(8):
        weekly_history.append({
            "week_start": base_date + timedelta(weeks=w),
            "referred_count": 5,
            "avg_lot_size": 1.2,
            "micro_trade_pct": 5.0,
            "withdrawal_72h_pct": 2.0,
        })
    # Weeks 9 and 10: abrupt shift
    for w in range(8, 10):
        weekly_history.append({
            "week_start": base_date + timedelta(weeks=w),
            "referred_count": 65,
            "avg_lot_size": 0.01,
            "micro_trade_pct": 95.0,
            "withdrawal_72h_pct": 88.0,
        })

    analyzer = TemporalDriftAnalyzer()
    drift = analyzer.detect_behavioral_shift("P-SHIFTING-01", weekly_history)

    assert drift.partner_id == "P-SHIFTING-01"
    assert drift.shift_detected is True
    assert drift.shift_magnitude >= 0.75
    assert "pre-fraud signature" in drift.alert_message.lower() or "behavior shift" in drift.alert_message.lower()
