"""Supervised Alert Triage Scorer and Queue Prioritizer (US1 / P1 MVP).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 1)
- .specify/memory/constitution.md (Principles I, VI)

Compresses ~2,000 raw surveillance alerts into <= 50 high-confidence investigation cases,
retaining >= 90% of true positive laundering events while filtering false alarms.
"""

import math
from datetime import datetime

import numpy as np

from eios.aml.models import (
    AMLAlert,
    AMLPriorityTier,
)
from eios.ingestion.hot_state import HotStateEngine


class AlertTriageScorer:
    """Calibrated alert prioritization model and queue compressor."""

    def __init__(
        self, hot_state: HotStateEngine | None = None, min_score_threshold: float = 0.60
    ) -> None:
        self.hot_state = hot_state
        self.min_score_threshold = min_score_threshold

    def extract_features(self, alert: AMLAlert) -> dict[str, float]:
        """Extract multi-source features from alert attributes."""
        attrs = alert.attributes

        peer_z = float(attrs.get("peer_z_score", 0.0))
        hours_since_kyc = float(attrs.get("hours_since_kyc", 500.0))
        dw_ratio = float(attrs.get("deposit_withdrawal_ratio", 0.5))
        mule_size = float(attrs.get("mule_cluster_size", 1.0))
        market_risk = float(attrs.get("market_risk_pct", 0.15))
        amount = float(alert.amount_usd)

        return {
            "peer_z": peer_z,
            "hours_since_kyc": hours_since_kyc,
            "dw_ratio": dw_ratio,
            "mule_size": mule_size,
            "market_risk": market_risk,
            "amount": amount,
        }

    def compute_calibrated_risk(self, features: dict[str, float]) -> float:
        """Compute calibrated probability of money laundering P(illicit | X)."""
        peer_z = features["peer_z"]
        kyc_h = features["hours_since_kyc"]
        dw_ratio = features["dw_ratio"]
        mule_size = features["mule_size"]
        market_risk = features["market_risk"]

        # 1. Structuring & KYC Recency component (high within 72h of KYC)
        if kyc_h <= 72.0:
            kyc_factor = math.exp(-kyc_h / 36.0)  # decays as hours increase towards 72
        else:
            kyc_factor = 0.05

        # 2. Deposit-Withdrawal Turnover Symmetry (ratio near 1.0 indicates pass-through laundering)
        dw_factor = math.exp(-abs(dw_ratio - 1.0) * 4.0) if dw_ratio > 0 else 0.1

        # 3. Market Risk Exposure Penalty (near zero profit/loss with short hold is synthetic)
        if market_risk <= 0.01:
            zero_risk_boost = 1.0 - (market_risk / 0.01)
        else:
            zero_risk_boost = 0.0

        # 4. Network Mule Component
        mule_factor = math.log1p(max(0.0, mule_size - 1.0)) / math.log(20.0)
        mule_factor = min(1.0, max(0.0, mule_factor))

        # 5. Peer Anomaly Component
        z_factor = 1.0 / (1.0 + math.exp(-(peer_z - 2.0)))

        # Logit combination
        logit = (
            2.2 * z_factor
            + 2.8 * kyc_factor * dw_factor * (0.5 + 0.5 * zero_risk_boost)
            + 3.0 * mule_factor
            - 1.5 * min(1.0, market_risk / 0.05)  # hard negative suppression for genuine risk
            - 1.2
        )

        calibrated_prob = 1.0 / (1.0 + math.exp(-logit))
        return round(float(np.clip(calibrated_prob, 0.01, 0.99)), 4)

    def score_single_alert(self, alert: AMLAlert) -> AMLAlert:
        """Score an individual alert and update priority tier."""
        features = self.extract_features(alert)
        risk = self.compute_calibrated_risk(features)

        # Assign priority tier based on calibrated risk
        if risk >= 0.85:
            tier = AMLPriorityTier.CRITICAL
        elif risk >= 0.70:
            tier = AMLPriorityTier.HIGH
        elif risk >= 0.40:
            tier = AMLPriorityTier.MEDIUM
        else:
            tier = AMLPriorityTier.LOW

        return AMLAlert(
            alert_id=alert.alert_id,
            client_id=alert.client_id,
            trigger_type=alert.trigger_type,
            risk_score=risk,
            priority_tier=tier,
            typology=alert.typology,
            amount_usd=alert.amount_usd,
            triggered_at=alert.triggered_at,
            is_triage_top50=alert.is_triage_top50,
            attributes=alert.attributes,
        )

    def score_queue(self, alerts: list[AMLAlert]) -> list[AMLAlert]:
        """Score all alerts and mark the top 50 prioritized cases while preserving input order."""
        scored = [self.score_single_alert(a) for a in alerts]

        # Identify top 50 alert IDs by risk score
        sorted_indices = sorted(
            range(len(scored)),
            key=lambda i: (scored[i].risk_score, scored[i].amount_usd),
            reverse=True,
        )
        top50_ids = set()
        for rank, idx in enumerate(sorted_indices):
            if rank < 50 and scored[idx].risk_score >= self.min_score_threshold:
                top50_ids.add(scored[idx].alert_id)

        # Return in original order with is_triage_top50 marked
        result: list[AMLAlert] = []
        for a in scored:
            is_top = a.alert_id in top50_ids
            result.append(
                AMLAlert(
                    alert_id=a.alert_id,
                    client_id=a.client_id,
                    trigger_type=a.trigger_type,
                    risk_score=a.risk_score,
                    priority_tier=AMLPriorityTier.CRITICAL if is_top else a.priority_tier,
                    typology=a.typology,
                    amount_usd=a.amount_usd,
                    triggered_at=a.triggered_at,
                    is_triage_top50=is_top,
                    attributes=a.attributes,
                )
            )

        return result

    def get_top_k_worklist(self, scored_alerts: list[AMLAlert], k: int = 50) -> list[AMLAlert]:
        """Return the prioritized top-k worklist for compliance investigators."""
        sorted_alerts = sorted(scored_alerts, key=lambda a: a.risk_score, reverse=True)
        return sorted_alerts[:k]

    def persist_scored_alerts(self, alerts: list[AMLAlert]) -> int:
        """Persist scored alerts to DuckDB hot-state aml_alert_scores table."""
        if not self.hot_state:
            return 0

        cursor = self.hot_state.get_cursor()
        inserted = 0
        for a in alerts:
            ts_str = (
                a.triggered_at.strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(a.triggered_at, datetime)
                else str(a.triggered_at)
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO aml_alert_scores (
                    alert_id, client_id, trigger_type, risk_score, priority_tier,
                    typology, amount_usd, is_triage_top50, triggered_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    a.alert_id,
                    a.client_id,
                    a.trigger_type.value
                    if hasattr(a.trigger_type, "value")
                    else str(a.trigger_type),
                    a.risk_score,
                    a.priority_tier.value
                    if hasattr(a.priority_tier, "value")
                    else str(a.priority_tier),
                    a.typology.value if hasattr(a.typology, "value") else str(a.typology),
                    a.amount_usd,
                    a.is_triage_top50,
                    ts_str,
                ],
            )
            inserted += 1
        return inserted
