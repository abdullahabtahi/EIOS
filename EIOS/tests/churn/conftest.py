"""Pytest fixtures and seeded golden test datasets for Partner Churn Radar (T003)."""

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from eios.churn.models import RiskTier
from eios.ingestion.hot_state import HotStateEngine


@pytest.fixture
def golden_personas() -> dict[str, dict[str, Any]]:
    """Defines the 3 canonical evaluation and demo personas."""
    return {
        "P-CHURN-DRIFT": {
            "partner_id": "P-CHURN-DRIFT",
            "tier": "VIP_MASTER",
            "region": "IDN_MYS",
            "tenure_months": 18,
            "value_at_risk": 45000.0,
            "status": "ACTIVE",
            "planted_anomaly": "LOGIN_DECAY_AND_COMPETITOR_POACHING",
            "expected_tier": RiskTier.HIGH,
            "min_expected_hazard": 0.60,
        },
        "P-HARD-NEG-VACATION": {
            "partner_id": "P-HARD-NEG-VACATION",
            "tier": "TIER_2",
            "region": "EUR_DEU",
            "tenure_months": 24,
            "value_at_risk": 8500.0,
            "status": "ACTIVE",
            "planted_anomaly": "SEASONAL_HOLIDAY_DIP",
            "expected_tier": RiskTier.LOW,
            "max_expected_hazard": 0.30,
        },
        "P-COHORT-SEA-CLUSTER": {
            "region_id": "IDN_MYS",
            "partner_count": 15,
            "combined_value_at_risk": 180000.0,
            "planted_anomaly": "SYNCHRONIZED_REGIONAL_COMPETITOR_POACHING",
        },
    }


@pytest.fixture
def seeded_hot_state() -> HotStateEngine:  # noqa: PLR0912
    """Provides an in-memory DuckDB HotStateEngine initialized with Churn Radar tables."""
    hot_state = HotStateEngine(db_path=":memory:")
    conn = hot_state._conn
    hot_state.conn = conn

    # 1. Base tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS partner_360 (
            partner_id VARCHAR PRIMARY KEY,
            tier VARCHAR,
            region VARCHAR,
            tenure_months INTEGER,
            value_at_risk DOUBLE,
            manager_id VARCHAR,
            status VARCHAR
        );

        CREATE TABLE IF NOT EXISTS partner_engagement_signals (
            partner_id VARCHAR,
            date DATE,
            logins INTEGER,
            referrals INTEGER,
            ftd_count INTEGER,
            conversion_rate DOUBLE,
            clicks INTEGER
        );

        CREATE TABLE IF NOT EXISTS partner_comms (
            message_id VARCHAR PRIMARY KEY,
            partner_id VARCHAR,
            channel VARCHAR,
            sentiment VARCHAR,
            text VARCHAR,
            timestamp TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS commission_ledger (
            entry_id VARCHAR PRIMARY KEY,
            partner_id VARCHAR,
            client_id VARCHAR,
            basis VARCHAR,
            amount DOUBLE,
            currency VARCHAR,
            paid_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competitor_benchmarks (
            competitor VARCHAR,
            date DATE,
            region VARCHAR,
            payout_rate DOUBLE,
            spread_pips DOUBLE,
            promo_event VARCHAR
        );

        -- Churn Radar Specific Tables
        CREATE TABLE IF NOT EXISTS churn_radar_scores (
            partner_id VARCHAR PRIMARY KEY,
            as_of_date DATE NOT NULL,
            hazard_probability_30d DOUBLE NOT NULL,
            priority_score DOUBLE NOT NULL,
            risk_tier VARCHAR NOT NULL,
            intervention_window VARCHAR NOT NULL,
            change_point_flag BOOLEAN NOT NULL,
            top_driver_family VARCHAR NOT NULL,
            top_driver_metric VARCHAR NOT NULL,
            top_driver_delta DOUBLE NOT NULL,
            narrative_summary VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS churn_cohort_alerts (
            alert_id VARCHAR PRIMARY KEY,
            region_id VARCHAR NOT NULL,
            partner_count INTEGER NOT NULL,
            aggregate_value_at_risk DOUBLE NOT NULL,
            p_value DOUBLE NOT NULL,
            common_driver VARCHAR NOT NULL,
            recommended_playbook VARCHAR NOT NULL,
            detected_at TIMESTAMP NOT NULL,
            status VARCHAR DEFAULT 'ACTIVE'
        );

        CREATE TABLE IF NOT EXISTS decision_outcomes_ledger (
            outcome_id VARCHAR PRIMARY KEY,
            intent_id VARCHAR NOT NULL,
            partner_id VARCHAR NOT NULL,
            playbook_id VARCHAR NOT NULL,
            treatment_assigned INTEGER NOT NULL,
            propensity_score DOUBLE NOT NULL,
            observed_retained_revenue_60d DOUBLE NOT NULL,
            actual_churn_60d BOOLEAN NOT NULL,
            recorded_at TIMESTAMP NOT NULL
        );
    """)

    # Seed P-CHURN-DRIFT
    conn.execute("""
        INSERT INTO partner_360 VALUES
        ('P-CHURN-DRIFT', 'VIP_MASTER', 'IDN_MYS', 18, 45000.0, 'MGR-01', 'ACTIVE'),
        ('P-HARD-NEG-VACATION', 'TIER_2', 'EUR_DEU', 24, 8500.0, 'MGR-02', 'ACTIVE');
    """)

    # Seed engagement history over 28 days
    base_date = date.today() - timedelta(days=28)
    for i in range(28):
        current_date = base_date + timedelta(days=i)
        is_weekend = current_date.weekday() >= 5

        # P-CHURN-DRIFT: 40% decay over last 14 days
        if is_weekend:
            drift_logins = 0
            drift_clicks = 0
        else:
            if i < 14:
                drift_logins = 20
                drift_clicks = 150
            else:
                drift_logins = max(2, int(20 * (1 - 0.40 * ((i - 13) / 14))))
                drift_clicks = max(15, int(150 * (1 - 0.35 * ((i - 13) / 14))))

        conn.execute(
            """
            INSERT INTO partner_engagement_signals VALUES
            ('P-CHURN-DRIFT', ?, ?, 5, 2, 0.08, ?)
        """,
            (current_date, drift_logins, drift_clicks),
        )

        # P-HARD-NEG-VACATION: 2 weeks holiday in the middle (days 10 to 23 = 0 logins, then recovers)
        if is_weekend:
            vac_logins = 0
            vac_clicks = 0
        else:
            if 10 <= i < 24:
                vac_logins = 0
                vac_clicks = 0
            else:
                vac_logins = 12
                vac_clicks = 80

        conn.execute(
            """
            INSERT INTO partner_engagement_signals VALUES
            ('P-HARD-NEG-VACATION', ?, ?, 3, 1, 0.05, ?)
        """,
            (current_date, vac_logins, vac_clicks),
        )

    # Seed support ticket for P-CHURN-DRIFT
    conn.execute(
        """
        INSERT INTO partner_comms VALUES
        ('TICK-8492', 'P-CHURN-DRIFT', 'TICKET', 'NEGATIVE',
         'Competitor XM is offering 60% revshare and zero spread markups in Southeast Asia. Can you match?',
         ?)
    """,
        (datetime.now(UTC) - timedelta(days=3),),
    )

    # Seed 15 SEA cohort partners
    for p_idx in range(1, 16):
        pid = f"P-SEA-{p_idx:02d}"
        conn.execute(
            """
            INSERT INTO partner_360 VALUES (?, 'TIER_1', 'IDN_MYS', 12, 12000.0, 'MGR-SEA', 'ACTIVE')
        """,
            (pid,),
        )
        for i in range(28):
            current_date = base_date + timedelta(days=i)
            # Synchronized drop in last 10 days (FTDs and logins decay)
            if i >= 18:
                logins = 1
                ftds = 0
            else:
                logins = 10
                ftds = 3
            conn.execute(
                """
                INSERT INTO partner_engagement_signals VALUES (?, ?, ?, 1, ?, 0.04, 30)
            """,
                (pid, current_date, logins, ftds),
            )

        # Seed competitor inquiry ticket for SEA cohort
        conn.execute(
            """
            INSERT INTO partner_comms VALUES
            (?, ?, 'TICKET', 'NEGATIVE',
             'Exness and XM zero-swap promotion in Indonesia/Malaysia is pulling my sub-affiliates.',
             ?)
        """,
            (f"TICK-SEA-{p_idx:02d}", pid, datetime.now(UTC) - timedelta(days=2)),
        )

    return hot_state
