"""Unit tests for Peer Cohort Baselines and Cold-Start Anomaly Scorer (US5 / P2).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 5)
"""

from eios.aml.peer_baseline import PeerBaselineEngine


def test_peer_baseline_cold_start_evaluation() -> None:
    """Test cold-start account (< 5 txns) evaluated against peer cohort."""
    engine = PeerBaselineEngine()

    # Register peer cohort: Tier 1, Retail, Organic Web
    engine.register_cohort(
        cohort_id="TIER1_RETAIL_ORGANIC",
        median_deposit=250.0,
        mad_deposit=100.0,
        median_velocity_24h=1.0,
    )

    # 1. Normal new signup deposit
    clean_score = engine.evaluate_client_anomaly(
        client_id="C-NEW-CLEAN-01",
        cohort_id="TIER1_RETAIL_ORGANIC",
        deposit_amount=300.0,
        transaction_count=1,
        tenure_days=2.0,
    )
    assert clean_score.anomaly_score < 0.35
    assert clean_score.is_outlier is False
    assert clean_score.evaluation_mode == "COHORT_ONLY"

    # 2. Outlier new signup deposit (exceeds cohort by > 4.0 sigma)
    outlier_score = engine.evaluate_client_anomaly(
        client_id="C-NEW-ANOMALY-01",
        cohort_id="TIER1_RETAIL_ORGANIC",
        deposit_amount=4500.0,
        transaction_count=1,
        tenure_days=2.0,
    )
    assert outlier_score.anomaly_score >= 0.85
    assert outlier_score.is_outlier is True
    assert outlier_score.evaluation_mode == "COHORT_ONLY"


def test_peer_baseline_mature_account_personal_distribution() -> None:
    """Test established account (>= 20 txns) evaluated against personal baseline."""
    engine = PeerBaselineEngine()
    engine.register_cohort(
        cohort_id="TIER1_RETAIL_ORGANIC",
        median_deposit=250.0,
        mad_deposit=100.0,
    )

    # Register established personal history for high-net-worth client
    engine.register_client_personal_baseline(
        client_id="C-MATURE-HNW-01",
        median_deposit=10000.0,
        mad_deposit=2000.0,
        transaction_count=35,
    )

    # 1. High deposit conforming to personal baseline (exceeds peer, but normal for user)
    conforming_score = engine.evaluate_client_anomaly(
        client_id="C-MATURE-HNW-01",
        cohort_id="TIER1_RETAIL_ORGANIC",
        deposit_amount=12000.0,
        transaction_count=35,
        tenure_days=180.0,
    )
    assert conforming_score.anomaly_score < 0.40
    assert conforming_score.is_outlier is False
    assert conforming_score.evaluation_mode == "PERSONAL_DOMINANT"

    # 2. Severe personal deviation
    spike_score = engine.evaluate_client_anomaly(
        client_id="C-MATURE-HNW-01",
        cohort_id="TIER1_RETAIL_ORGANIC",
        deposit_amount=85000.0,
        transaction_count=35,
        tenure_days=180.0,
    )
    assert spike_score.anomaly_score >= 0.85
    assert spike_score.is_outlier is True
