"""Unit and evaluation tests for Supervised Alert Triage Scorer (US1 / P1 MVP).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 1, SC-001)
"""

from datetime import datetime
from eios.aml.models import AMLAlert, AMLPriorityTier, AMLTriggerType, AMLTypology
from eios.aml.triage_scorer import AlertTriageScorer
from eios.ingestion.hot_state import HotStateEngine


def test_triage_scorer_extracts_features_and_scores_alert() -> None:
    """Test feature extraction and calibrated risk calculation on a single alert."""
    scorer = AlertTriageScorer()
    alert = AMLAlert(
        alert_id="ALT-TEST-01",
        client_id="C-TEST-01",
        trigger_type=AMLTriggerType.ROUND_TRIP_SEQUENCE,
        risk_score=0.5,
        priority_tier=AMLPriorityTier.HIGH,
        typology=AMLTypology.MICRO_PNL_WASH,
        amount_usd=500.0,
        triggered_at=datetime(2026, 10, 1, 10, 0, 0),
        attributes={
            "peer_z_score": 4.5,
            "hours_since_kyc": 12.0,
            "deposit_withdrawal_ratio": 0.99,
            "market_risk_pct": 0.0002,
            "mule_cluster_size": 1,
        },
    )

    scored = scorer.score_single_alert(alert)
    assert scored.risk_score >= 0.85
    assert scored.priority_tier in (AMLPriorityTier.CRITICAL, AMLPriorityTier.HIGH)


def test_triage_scorer_compresses_2000_queue_to_top_50(
    synthetic_alert_queue: list[AMLAlert],
) -> None:
    """Verify triage scorer compresses 2,000 alerts to <= 50 and retains >= 90% true positives."""
    scorer = AlertTriageScorer()
    assert len(synthetic_alert_queue) == 2000

    scored_queue = scorer.score_queue(synthetic_alert_queue)
    assert len(scored_queue) == 2000

    top_50_worklist = scorer.get_top_k_worklist(scored_queue, k=50)
    assert len(top_50_worklist) == 50

    # Count how many planted true positives are in the top-50 worklist
    planted_in_top50 = sum(
        1 for alert in top_50_worklist if alert.attributes.get("is_planted_tp", False)
    )
    retention_rate = planted_in_top50 / 50.0  # 50 planted TPs in queue

    print(f"\nPlanted True Positives captured in top-50: {planted_in_top50}/50 ({retention_rate:.1%})")
    assert retention_rate >= 0.90, (
        f"Failed true positive retention target: {retention_rate:.1%} < 90.0%"
    )

    # Verify hard negatives are suppressed from the top 50
    hard_negs_in_top50 = sum(
        1 for alert in top_50_worklist if alert.attributes.get("is_hard_negative", False)
    )
    print(f"Hard negatives in top-50: {hard_negs_in_top50}/100")
    assert hard_negs_in_top50 <= 3, f"Too many hard negatives in top 50: {hard_negs_in_top50}"


def test_triage_scorer_persists_to_hot_state(
    synthetic_alert_queue: list[AMLAlert],
) -> None:
    """Test hot-state DuckDB persistence into aml_alert_scores table."""
    hot_state = HotStateEngine()
    scorer = AlertTriageScorer(hot_state=hot_state)

    scored_queue = scorer.score_queue(synthetic_alert_queue[:100])
    persisted_count = scorer.persist_scored_alerts(scored_queue)
    assert persisted_count == 100

    cursor = hot_state.get_cursor()
    row_count = cursor.execute("SELECT count(*) FROM aml_alert_scores").fetchone()[0]
    assert row_count == 100

    top_count = cursor.execute("SELECT count(*) FROM aml_alert_scores WHERE is_triage_top50 = TRUE").fetchone()[0]
    assert top_count >= 1
