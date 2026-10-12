"""Batch scoring pipeline for Partner Churn Radar (T012, T026).

Orchestrates:
1. Feature extraction from L1 Data Products in DuckDB Hot State
2. Discrete-Time Hazard Model prediction
3. Priority scoring (hazard * value_at_risk)
4. Persisting results into DuckDB churn_radar_scores table
5. Running cohort anomaly detection and persisting alerts into churn_cohort_alerts table
"""

from datetime import date, datetime
from typing import Any
import duckdb
import pandas as pd

from eios.churn.change_point import SeasonalityChangePointDetector
from eios.churn.cohort_detector import CohortRiskDetector
from eios.churn.features import PartnerFeatureExtractor
from eios.churn.hazard_model import DiscreteTimeHazardModel
from eios.ingestion.hot_state import HotStateEngine


class ChurnRadarPipeline:
    """Batch scoring coordinator for Partner Churn Radar."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection | None = None,
        hazard_model: DiscreteTimeHazardModel | None = None,
        hot_state: HotStateEngine | None = None,
    ) -> None:
        if hot_state is not None:
            self.conn = hot_state.get_cursor()
            self.hot_state = hot_state
        elif conn is not None:
            if isinstance(conn, HotStateEngine):
                self.conn = conn.get_cursor()
                self.hot_state = conn
            else:
                self.conn = conn
                self.hot_state = None
        else:
            raise ValueError("Either conn or hot_state must be provided.")

        self.extractor = PartnerFeatureExtractor(self.conn)
        self.hazard_model = hazard_model or DiscreteTimeHazardModel()
        self.cohort_detector = CohortRiskDetector(self.conn)
        self.change_point_detector = SeasonalityChangePointDetector()

    def run_scoring_job(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Executes full batch scoring and hot state persistence."""
        if as_of_date is None:
            as_of_date = date.today()

        # 1. Extract feature matrix
        df_features = self.extractor.extract_partner_features(as_of_date)
        if df_features.empty:
            return pd.DataFrame()

        # Seasonality change-point filter (FR-004 / US3)
        seasonal_flags = []
        for pid in df_features["partner_id"]:
            hist_rows = self.conn.execute("""
                SELECT date, logins 
                FROM partner_engagement_signals 
                WHERE partner_id = ? 
                ORDER BY date
            """, [str(pid)]).fetchall()
            if hist_rows and len(hist_rows) >= 7:
                hist_df = pd.DataFrame(hist_rows, columns=["date", "volume"])
                cp_res = self.change_point_detector.detect_change_point(hist_df, metric_col="volume")
                is_dip = (cp_res["reason"] == "SEASONAL_DIP_RECOVERED")
                seasonal_flags.append(is_dip)
            else:
                seasonal_flags.append(False)

        df_features["seasonal_dip_flag"] = seasonal_flags

        # 2. Predict 30-day hazard probabilities and risk tiers
        df_scored = self.hazard_model.predict_30d_hazard(df_features)

        # 3. Calculate Value-at-Risk priority score
        df_scored["priority_score"] = (
            df_scored["hazard_probability_30d"] * df_scored["value_at_risk"]
        ).round(2)

        # 4. Identify top driver signal family and delta
        df_scored["top_driver_family"] = "BEHAVIORAL"
        df_scored["top_driver_metric"] = "login_velocity_decay_3w"
        df_scored["top_driver_delta"] = df_scored["login_velocity_decay_3w"]

        # If competitor mentions present, prioritize as top driver
        comp_mask = df_scored["competitor_mention_flag"] > 0
        df_scored.loc[comp_mask, "top_driver_family"] = "COMPETITIVE"
        df_scored.loc[comp_mask, "top_driver_metric"] = "competitor_mention_flag"
        df_scored.loc[comp_mask, "top_driver_delta"] = 1.0

        # Change point default flag
        if "change_point_flag" not in df_scored.columns:
            df_scored["change_point_flag"] = False

        # 5. Persist into DuckDB churn_radar_scores
        for _, row in df_scored.iterrows():
            self.conn.execute("""
                INSERT OR REPLACE INTO churn_radar_scores (
                    partner_id,
                    as_of_date,
                    hazard_probability_30d,
                    priority_score,
                    risk_tier,
                    intervention_window,
                    change_point_flag,
                    top_driver_family,
                    top_driver_metric,
                    top_driver_delta,
                    narrative_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row["partner_id"]),
                as_of_date,
                float(row["hazard_probability_30d"]),
                float(row["priority_score"]),
                str(row["risk_tier"]),
                str(row["intervention_window"]),
                bool(row["change_point_flag"]),
                str(row["top_driver_family"]),
                str(row["top_driver_metric"]),
                float(row["top_driver_delta"]),
                f"{row['risk_tier']} risk partner driven by {row['top_driver_family']} signals."
            ))

        # 6. Run cohort anomaly detection and persist alerts (T026)
        alerts = self.cohort_detector.detect_cohort_anomalies(as_of_date=as_of_date)
        if alerts:
            self.cohort_detector.persist_alerts(alerts)

        return df_scored

    def run_daily_scoring(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Alias for run_scoring_job."""
        return self.run_scoring_job(as_of_date=as_of_date)
