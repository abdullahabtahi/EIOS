"""Batch Partner Fraud Sentinel Coordinator Pipeline (T041).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md
- specs/009-partner-fraud/plan.md §4
- specs/009-partner-fraud/quickstart.md (Scenario 2)
"""

from datetime import UTC, date, datetime
import duckdb
import pandas as pd

from eios.fraud.bonus_abuse import BonusAbuseScorer
from eios.fraud.dossier import FraudDossierAssembler
from eios.fraud.models import PartnerFraudCase, TradingPairCorrelation
from eios.fraud.pair_detector import TimeBucketedPairDetector
from eios.fraud.ring_attribution import ReferralRingAttributionEngine
from eios.fraud.traffic_anomaly import TrafficAnomalyDetector
from eios.ingestion.hot_state import HotStateEngine


class PartnerFraudPipeline:
    """Batch scoring and detection coordinator for Partner Fraud Sentinel."""

    def __init__(self, hot_state: HotStateEngine) -> None:
        self.hot_state = hot_state
        self.pair_detector = TimeBucketedPairDetector()
        self.ring_engine = ReferralRingAttributionEngine()
        self.bonus_scorer = BonusAbuseScorer()
        self.traffic_detector = TrafficAnomalyDetector()
        self.dossier_assembler = FraudDossierAssembler()

    def run_pipeline(
        self,
        trade_df: pd.DataFrame | None = None,
        tree_records: list[dict] | None = None,
        client_records: list[dict] | None = None,
        funnel_records: list[dict] | None = None,
    ) -> dict[str, int]:
        """Execute full batch fraud pipeline and persist into DuckDB hot state."""
        cursor = self.hot_state.get_cursor()
        now = datetime.now(UTC)

        # 1. Trading Pair Detection
        if trade_df is None or trade_df.empty:
            # Query from hot state trading_activity if available
            try:
                trade_df = cursor.execute(
                    """
                    SELECT trade_id, account_id, partner_id, symbol,
                           order_type as direction, volume as lots,
                           open_ts as timestamp, profit_loss as pnl_usd,
                           5.0 as commission_usd
                    FROM trading_activity
                    """
                ).df()
            except Exception:
                trade_df = pd.DataFrame()

        detected_pairs: list[TradingPairCorrelation] = []
        if not trade_df.empty:
            detected_pairs = self.pair_detector.detect_pairs(trade_df)
            self.pair_detector.persist_pairs_to_hot_state(self.hot_state, detected_pairs)

        # 2. Network Referral Tree Builder
        if tree_records is None:
            try:
                tree_df = cursor.execute("SELECT * FROM partner_referral_tree").df()
                tree_records = tree_df.to_dict("records")
            except Exception:
                tree_records = []

        if tree_records:
            self.ring_engine.build_graph(tree_records)

        # 3. Identify all distinct active partners
        partner_ids = set()
        if not trade_df.empty and "partner_id" in trade_df.columns:
            partner_ids.update(trade_df["partner_id"].unique())
        if tree_records:
            for t in tree_records:
                if "partner_id" in t:
                    partner_ids.add(t["partner_id"])
                if "child_id" in t:
                    partner_ids.add(t["child_id"])

        scores_inserted = 0
        cases_inserted = 0

        # 4. Process each partner and populate partner_fraud_scores and partner_fraud_cases
        for pid in partner_ids:
            ring_attr = self.ring_engine.attribute_partner_ring(pid) if tree_records else None
            bonus_profile = self.bonus_scorer.score_partner_portfolio(pid, client_records or [])
            traffic_signal = (
                next((s for s in self.traffic_detector.evaluate_funnels(funnel_records or []) if s.partner_id == pid), None)
                if funnel_records
                else None
            )

            # Check pairs involving pid
            p_pairs = [p for p in detected_pairs if p.partner_a == pid or p.partner_b == pid]

            # Assemble Case Dossier
            case: PartnerFraudCase = self.dossier_assembler.assemble_dossier(
                partner_id=pid,
                trading_pairs=p_pairs,
                ring_attribution=ring_attr,
                bonus_profile=bonus_profile,
                traffic_signal=traffic_signal,
            )

            # Persist to partner_fraud_scores table
            cursor.execute(
                """
                INSERT OR REPLACE INTO partner_fraud_scores (
                    partner_id, master_partner_id, tier_level, primary_typology,
                    fraud_risk_score, client_quality_index, opposite_trading_pair_count,
                    bonus_abuse_probability, bot_traffic_probability, total_exposure_usd,
                    computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    pid,
                    case.master_partner_id,
                    ring_attr.hierarchy_depth if ring_attr else 1,
                    case.primary_typology.value,
                    case.fraud_risk_score,
                    bonus_profile.client_quality_index,
                    len(p_pairs),
                    bonus_profile.abuse_probability,
                    traffic_signal.bot_traffic_probability if traffic_signal else 0.0,
                    case.total_exposure_usd,
                    now,
                ],
            )
            scores_inserted += 1

            # If risk score exceeds threshold, persist to partner_fraud_cases table
            if case.fraud_risk_score >= 0.50:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO partner_fraud_cases (
                        case_id, partner_id, master_partner_id, primary_typology,
                        fraud_risk_score, total_exposure_usd, confidence_level,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        case.case_id,
                        case.partner_id,
                        case.master_partner_id,
                        case.primary_typology.value,
                        case.fraud_risk_score,
                        case.total_exposure_usd,
                        case.confidence_level,
                        case.status,
                        now,
                    ],
                )
                cases_inserted += 1

        return {
            "pairs_detected": len(detected_pairs),
            "scores_inserted": scores_inserted,
            "cases_inserted": cases_inserted,
        }
