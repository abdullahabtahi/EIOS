"""Feature extraction pipeline for Partner Churn Radar across 5 signal families (T007).

Extracts features from DuckDB Hot State L1 Data Products:
- DP6: partner_360
- DP7: partner_referral_tree
- DP8: commission_ledger
- DP9: partner_engagement_signals
- DP10: partner_comms
- DP11: financial_pnl
- DP12: competitor_benchmarks
"""

from datetime import date

import duckdb
import numpy as np
import pandas as pd

from eios.churn.models import SignalContribution, SignalFamily


class PartnerFeatureExtractor:
    """Extracts normalized multi-signal person-period features from DuckDB hot state."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def extract_partner_features(self, as_of_date: date | None = None) -> pd.DataFrame:
        """Extract multi-signal feature vector for all active partners."""
        if as_of_date is None:
            as_of_date = date.today()

        query = """
            WITH partners AS (
                SELECT partner_id, tier, region, tenure_months, value_at_risk
                FROM partner_360
                WHERE status = 'ACTIVE'
            ),
            behav_recent AS (
                SELECT 
                    partner_id,
                    SUM(CASE WHEN date >= ? - INTERVAL 14 DAY THEN logins ELSE 0 END) AS logins_recent,
                    SUM(CASE WHEN date < ? - INTERVAL 14 DAY AND date >= ? - INTERVAL 28 DAY THEN logins ELSE 0 END) AS logins_prior,
                    SUM(CASE WHEN date >= ? - INTERVAL 14 DAY THEN ftd_count ELSE 0 END) AS ftds_recent,
                    SUM(CASE WHEN date < ? - INTERVAL 14 DAY AND date >= ? - INTERVAL 28 DAY THEN ftd_count ELSE 0 END) AS ftds_prior,
                    SUM(clicks) AS total_clicks,
                    MAX(date) AS last_active_date
                FROM partner_engagement_signals
                WHERE date >= ? - INTERVAL 28 DAY
                GROUP BY partner_id
            ),
            comms AS (
                SELECT
                    partner_id,
                    COUNT(CASE WHEN sentiment IN ('NEGATIVE', 'ESCALATED') THEN 1 END) AS negative_tickets,
                    COUNT(CASE WHEN text ILIKE '%competitor%' OR text ILIKE '%exness%' OR text ILIKE '%xm%' THEN 1 END) AS competitor_mentions,
                    COUNT(*) AS total_tickets
                FROM partner_comms
                GROUP BY partner_id
            ),
            commissions AS (
                SELECT
                    partner_id,
                    SUM(CASE WHEN paid_at >= ? - INTERVAL 14 DAY THEN amount ELSE 0 END) AS comm_recent,
                    SUM(CASE WHEN paid_at < ? - INTERVAL 14 DAY AND paid_at >= ? - INTERVAL 28 DAY THEN amount ELSE 0 END) AS comm_prior
                FROM commission_ledger
                WHERE paid_at >= ? - INTERVAL 28 DAY
                GROUP BY partner_id
            )
            SELECT
                p.partner_id,
                p.tier,
                p.region,
                p.tenure_months,
                p.value_at_risk,
                COALESCE(b.logins_recent, 0) AS logins_recent,
                COALESCE(b.logins_prior, 0) AS logins_prior,
                COALESCE(b.ftds_recent, 0) AS ftds_recent,
                COALESCE(b.ftds_prior, 0) AS ftds_prior,
                COALESCE(b.total_clicks, 0) AS total_clicks,
                b.last_active_date,
                COALESCE(c.negative_tickets, 0) AS negative_tickets,
                COALESCE(c.competitor_mentions, 0) AS competitor_mentions,
                COALESCE(c.total_tickets, 0) AS total_tickets,
                COALESCE(m.comm_recent, 0.0) AS comm_recent,
                COALESCE(m.comm_prior, 0.0) AS comm_prior
            FROM partners p
            LEFT JOIN behav_recent b ON p.partner_id = b.partner_id
            LEFT JOIN comms c ON p.partner_id = c.partner_id
            LEFT JOIN commissions m ON p.partner_id = m.partner_id
        """

        params = [
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
            as_of_date,
        ]

        df = self.conn.execute(query, params).df()

        # Feature transformations across the 5 signal families
        # 1. Behavioral
        df["login_velocity_decay_3w"] = np.where(
            df["logins_prior"] > 0,
            (df["logins_prior"] - df["logins_recent"]) / np.maximum(df["logins_prior"], 1),
            0.0,
        )
        df["ftd_volume_delta_pct"] = np.where(
            df["ftds_prior"] > 0,
            (df["ftds_recent"] - df["ftds_prior"]) / np.maximum(df["ftds_prior"], 1),
            0.0,
        )
        df["inactive_days"] = np.where(
            df["last_active_date"].isna(),
            28.0,
            (pd.to_datetime(as_of_date) - pd.to_datetime(df["last_active_date"])).dt.days.fillna(
                28.0
            ),
        )

        # 2. Communication
        df["sentiment_negative_ratio"] = np.where(
            df["total_tickets"] > 0,
            df["negative_tickets"] / np.maximum(df["total_tickets"], 1),
            0.0,
        )
        df["unresolved_ticket_count"] = df["negative_tickets"]

        # 3. Relationship
        df["tenure_months_log"] = np.log1p(df["tenure_months"].clip(lower=0))

        # 4. Financial
        df["commission_velocity_30d"] = np.where(
            df["comm_prior"] > 0,
            (df["comm_recent"] - df["comm_prior"]) / np.maximum(df["comm_prior"], 1.0),
            0.0,
        )

        # 5. Competitive
        df["competitor_mention_flag"] = (df["competitor_mentions"] > 0).astype(float)

        return df

    def build_person_period_df(self, raw_df: pd.DataFrame, num_weeks: int = 4) -> pd.DataFrame:
        """Expands snapshot feature DataFrame into person-period observations for discrete hazard modeling."""
        records = []
        for _, row in raw_df.iterrows():
            for week in range(1, num_weeks + 1):
                rec = row.to_dict()
                rec["period_week"] = week
                # Temporal baseline interaction
                rec["week_baseline"] = week
                records.append(rec)
        return pd.DataFrame(records)

    def extract_signal_contributions(self, row: pd.Series) -> list[SignalContribution]:
        """Calculates deterministic signal contributions for explainability."""
        contributions: list[SignalContribution] = []

        # 1. Behavioral
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.BEHAVIORAL,
                metric_name="login_velocity_decay_3w",
                observed_value=float(row.get("logins_recent", 0)),
                baseline_value=float(row.get("logins_prior", 0)),
                relative_delta=float(row.get("login_velocity_decay_3w", 0.0)),
                hazard_weight=1.8,
                citation_ref="DP9:partner_engagement_signals",
            )
        )

        # 2. Communication
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.COMMUNICATION,
                metric_name="negative_tickets",
                observed_value=float(row.get("negative_tickets", 0)),
                baseline_value=0.0,
                relative_delta=float(row.get("sentiment_negative_ratio", 0.0)),
                hazard_weight=1.4,
                citation_ref="DP10:partner_comms",
            )
        )

        # 3. Relationship
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.RELATIONSHIP,
                metric_name="tenure_months",
                observed_value=float(row.get("tenure_months", 0)),
                baseline_value=12.0,
                relative_delta=float(row.get("tenure_months_log", 0.0)),
                hazard_weight=-0.8,
                citation_ref="DP6:partner_360",
            )
        )

        # 4. Financial
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.FINANCIAL,
                metric_name="commission_velocity_30d",
                observed_value=float(row.get("comm_recent", 0.0)),
                baseline_value=float(row.get("comm_prior", 0.0)),
                relative_delta=float(row.get("commission_velocity_30d", 0.0)),
                hazard_weight=1.5,
                citation_ref="DP8:commission_ledger",
            )
        )

        # 5. Competitive
        contributions.append(
            SignalContribution(
                signal_family=SignalFamily.COMPETITIVE,
                metric_name="competitor_mention_flag",
                observed_value=float(row.get("competitor_mention_flag", 0)),
                baseline_value=0.0,
                relative_delta=float(row.get("competitor_mention_flag", 0)),
                hazard_weight=2.2,
                citation_ref="DP10:partner_comms",
            )
        )

        return contributions
