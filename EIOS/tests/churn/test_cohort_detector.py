"""Unit tests for Systemic Regional & Cohort Risk Detection (T023 / US4)."""

from datetime import date

from eios.churn.cohort_detector import CohortRiskDetector
from eios.churn.pipeline import ChurnRadarPipeline
from eios.ingestion.hot_state import HotStateEngine


def test_cohort_detection_recovers_sea_cluster(seeded_hot_state: HotStateEngine):
    """Verify that 15 synchronized partners in SEA trigger a significant CohortAnomalyAlert."""
    # 1. Run pipeline to compute scores
    pipeline = ChurnRadarPipeline(hot_state=seeded_hot_state)
    pipeline.run_daily_scoring(as_of_date=date.today())

    # 2. Run cohort detector
    detector = CohortRiskDetector(hot_state=seeded_hot_state)
    alerts = detector.detect_cohort_anomalies(as_of_date=date.today())

    assert len(alerts) >= 1
    # Find SEA alert
    sea_alerts = [a for a in alerts if a.region_id == "IDN_MYS"]
    assert len(sea_alerts) == 1

    sea_alert = sea_alerts[0]
    assert sea_alert.partner_count >= 15
    assert set(f"P-SEA-{i:02d}" for i in range(1, 16)).issubset(set(sea_alert.affected_partner_ids))
    assert sea_alert.aggregate_value_at_risk_usd >= 150000.0
    assert sea_alert.p_value < 0.05
    assert "Regional" in sea_alert.recommended_playbook
    assert sea_alert.cohort_id != ""
    assert sea_alert.alert_id == sea_alert.cohort_id


def test_isolated_partner_does_not_trigger_cohort_alert():
    """Verify that an isolated partner disengagement in a region does not trigger a cohort alert."""
    engine = HotStateEngine(":memory:")
    cur = engine.get_cursor()

    cur.execute("""
        INSERT INTO partner_360 VALUES 
        ('P-ISO-1', 'TIER_1', 'LATAM_BRA', 12, 10000.0, 'MGR-1', 'ACTIVE'),
        ('P-ISO-2', 'TIER_1', 'LATAM_BRA', 12, 10000.0, 'MGR-1', 'ACTIVE'),
        ('P-ISO-3', 'TIER_1', 'LATAM_BRA', 12, 10000.0, 'MGR-1', 'ACTIVE'),
        ('P-ISO-4', 'TIER_1', 'LATAM_BRA', 12, 10000.0, 'MGR-1', 'ACTIVE'),
        ('P-ISO-5', 'TIER_1', 'LATAM_BRA', 12, 10000.0, 'MGR-1', 'ACTIVE');
    """)

    # Only 1 partner is high risk in LATAM_BRA
    cur.execute("""
        INSERT INTO churn_radar_scores VALUES 
        ('P-ISO-1', '2026-10-07', 0.85, 8500.0, 'HIGH', 'OPTIMAL', false, 'BEHAVIORAL', 'login_decay', -0.5, 'risk', CURRENT_TIMESTAMP),
        ('P-ISO-2', '2026-10-07', 0.10, 1000.0, 'LOW', 'STABLE', false, 'BEHAVIORAL', 'login_decay', 0.0, 'ok', CURRENT_TIMESTAMP),
        ('P-ISO-3', '2026-10-07', 0.12, 1200.0, 'LOW', 'STABLE', false, 'BEHAVIORAL', 'login_decay', 0.0, 'ok', CURRENT_TIMESTAMP),
        ('P-ISO-4', '2026-10-07', 0.08, 800.0, 'LOW', 'STABLE', false, 'BEHAVIORAL', 'login_decay', 0.0, 'ok', CURRENT_TIMESTAMP),
        ('P-ISO-5', '2026-10-07', 0.11, 1100.0, 'LOW', 'STABLE', false, 'BEHAVIORAL', 'login_decay', 0.0, 'ok', CURRENT_TIMESTAMP);
    """)

    detector = CohortRiskDetector(hot_state=engine)
    alerts = detector.detect_cohort_anomalies(as_of_date=date(2026, 10, 7))

    latam_alerts = [a for a in alerts if a.region_id == "LATAM_BRA"]
    assert len(latam_alerts) == 0


def test_omcp_get_high_risk_cohorts(seeded_hot_state: HotStateEngine):
    """Verify OMCP server get_high_risk_cohorts tool handler returns validated payload."""
    from eios.churn.models import CohortAlertsResponse
    from eios.ontology.omcp.server import OMCPServer

    # Score and detect
    pipeline = ChurnRadarPipeline(hot_state=seeded_hot_state)
    pipeline.run_daily_scoring(as_of_date=date.today())

    server = OMCPServer(hot_state=seeded_hot_state)
    res = server.call_tool("get_high_risk_cohorts", {})

    # Validate against Pydantic schema matching cohort-alerts-response.schema.json
    response_obj = CohortAlertsResponse.model_validate(res)
    assert len(response_obj.cohorts) >= 1
    assert any(c.region_id == "IDN_MYS" for c in response_obj.cohorts)
