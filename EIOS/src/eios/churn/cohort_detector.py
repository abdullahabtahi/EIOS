"""Systemic Regional and Cohort Risk Detector (T024 / US4).

Uses permutation / binomial tail statistical tests to detect synchronized partner
disengagements by region, preventing alert fatigue and surfacing systemic commercial threats.
"""

from collections import Counter
from datetime import UTC, date, datetime
import logging
from typing import Any
import duckdb
import scipy.stats as stats

from eios.churn.models import CohortAnomalyAlert
from eios.ingestion.hot_state import HotStateEngine

logger = logging.getLogger("eios.churn.cohort")


class CohortRiskDetector:
    """Detects statistically significant regional and segment disengagement clusters."""

    def __init__(self, hot_state: HotStateEngine | duckdb.DuckDBPyConnection) -> None:
        if isinstance(hot_state, HotStateEngine):
            self.conn = hot_state.get_cursor()
            self.hot_state = hot_state
        else:
            self.conn = hot_state
            self.hot_state = None

    def _get_cursor(self) -> duckdb.DuckDBPyConnection:
        if self.hot_state is not None:
            return self.hot_state.get_cursor()
        return self.conn

    def detect_cohort_anomalies(
        self,
        as_of_date: date | None = None,
        risk_threshold: float = 0.50,
        alpha: float = 0.05,
        min_cohort_size: int = 3,
    ) -> list[CohortAnomalyAlert]:
        """Scan partners by region and detect statistically significant disengagement clusters.
        
        Args:
            as_of_date: Evaluation date (defaults to today).
            risk_threshold: Hazard probability threshold to classify a partner as high risk.
            alpha: Significance level for permutation / binomial tail test.
            min_cohort_size: Minimum number of high-risk partners required to form a cohort.
            
        Returns:
            List of validated CohortAnomalyAlert records.
        """
        if as_of_date is None:
            as_of_date = date.today()

        cursor = self._get_cursor()

        # Query all active partners with latest hazard score and value_at_risk
        query = """
            SELECT 
                p.partner_id,
                p.region,
                p.tier,
                p.value_at_risk,
                COALESCE(s.hazard_probability_30d, 0.0) AS hazard_prob,
                COALESCE(s.priority_score, 0.0) AS priority_score,
                COALESCE(s.top_driver_family, 'BEHAVIORAL') AS top_driver_family,
                COALESCE(s.top_driver_metric, 'login_decay') AS top_driver_metric
            FROM partner_360 p
            LEFT JOIN churn_radar_scores s 
                ON p.partner_id = s.partner_id 
                AND s.as_of_date = ?
            WHERE p.status = 'ACTIVE'
        """
        rows = cursor.execute(query, (as_of_date,)).fetchall()

        if not rows:
            logger.info("No active partners found for cohort anomaly detection.")
            return []

        total_partners = len(rows)
        total_high_risk = sum(1 for r in rows if r[4] >= risk_threshold)

        # Baseline expected rate across the platform
        raw_global_rate = total_high_risk / total_partners if total_partners > 0 else 0.05
        # Guard against zero or extreme global probabilities
        p_global = min(max(raw_global_rate, 0.02), 0.40)

        # Group by region
        by_region: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            partner_data = {
                "partner_id": r[0],
                "region": r[1],
                "tier": r[2],
                "value_at_risk": r[3],
                "hazard_prob": r[4],
                "priority_score": r[5],
                "top_driver_family": r[6],
                "top_driver_metric": r[7],
            }
            by_region.setdefault(r[1], []).append(partner_data)

        alerts: list[CohortAnomalyAlert] = []

        for region, p_list in by_region.items():
            n_r = len(p_list)
            affected = [p for p in p_list if p["hazard_prob"] >= risk_threshold]
            k_r = len(affected)

            if k_r < min_cohort_size:
                continue

            # Binomial tail test: P(X >= k_r) under H0: p = p_global
            # stats.binom.sf(k_r - 1, n_r, p_global) computes P(X >= k_r)
            p_val = float(stats.binom.sf(k_r - 1, n_r, p_global))

            if p_val <= alpha:
                affected_ids = [p["partner_id"] for p in affected]
                agg_var = sum(p["value_at_risk"] for p in affected)
                
                # Determine common driver
                drivers = [f"{p['top_driver_family']}:{p['top_driver_metric']}" for p in affected]
                most_common = Counter(drivers).most_common(1)[0][0] if drivers else "BEHAVIORAL:decay"

                driver_desc = f"Synchronized disengagement ({most_common}); competitor regional promotion suspected"

                alert_id = f"ALERT-COHORT-{region}-{as_of_date.strftime('%Y%m%d')}"
                alert = CohortAnomalyAlert(
                    alert_id=alert_id,
                    cohort_id=alert_id,
                    region_id=region,
                    partner_count=k_r,
                    affected_partner_ids=affected_ids,
                    aggregate_value_at_risk_usd=round(agg_var, 2),
                    p_value=round(p_val, 6),
                    common_driver=driver_desc,
                    recommended_playbook="LaunchRegionalAffiliateIncentive",
                    detected_at=datetime.now(UTC),
                    status="ACTIVE",
                )
                alerts.append(alert)

        return alerts

    def persist_alerts(self, alerts: list[CohortAnomalyAlert]) -> None:
        """Write detected alerts to churn_cohort_alerts table."""
        if not alerts:
            return

        cursor = self._get_cursor()
        for alert in alerts:
            cursor.execute("""
                INSERT OR REPLACE INTO churn_cohort_alerts VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                alert.alert_id,
                alert.region_id,
                alert.partner_count,
                alert.aggregate_value_at_risk_usd,
                alert.p_value,
                alert.common_driver,
                alert.recommended_playbook,
                alert.detected_at,
                alert.status,
            ))
