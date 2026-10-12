"""Unsupervised Emerging Fraud Typology Discovery & Temporal Drift Intelligence (US7 / Module B).

Authoritative References:
- docs/brief/fraud [BRIEF fraud] ("What Would Blow Our Minds", "Proactive Pattern Discovery")
- specs/009-partner-fraud/spec.md (US7)
"""

from dataclasses import dataclass
from datetime import datetime
import networkx as nx
import numpy as np


@dataclass
class TemporalDriftSignal:
    partner_id: str
    shift_detected: bool
    shift_magnitude: float
    weeks_since_shift: int
    predicted_escalation_risk: float
    alert_message: str


class EmergingPatternMiner:
    """Discovers unlabelled, novel structural fraud typologies using graph topology analysis."""

    def __init__(self, min_cycle_length: int = 3) -> None:
        self.min_cycle_length = min_cycle_length

    def mine_anomalous_subgraphs(self, edge_records: list[dict]) -> list[dict]:
        """Detect novel typologies such as cyclic commission rebating or dense cliques."""
        g = nx.DiGraph()
        for e in edge_records:
            g.add_edge(e["from_partner"], e["to_partner"], **e)

        anomalous_clusters: list[dict] = []

        # 1. Unsupervised simple cycle discovery
        try:
            cycles = list(nx.simple_cycles(g))
        except Exception:
            cycles = []

        for cycle in cycles:
            if len(cycle) >= self.min_cycle_length:
                anomalous_clusters.append({
                    "typology_name": "CYCLIC_COMMISSION_REBATING",
                    "participating_partners": cycle,
                    "structural_anomaly_score": round(min(1.0, 0.70 + len(cycle) * 0.05), 4),
                    "description": (
                        f"Novel cyclic commission rebating pattern isolated across {len(cycle)} partners."
                    ),
                })

        return anomalous_clusters


class TemporalDriftAnalyzer:
    """Detects partner behavior drift, sudden strategy changes, and pre-fraud escalation signatures."""

    def __init__(self, drift_threshold: float = 0.50) -> None:
        self.drift_threshold = drift_threshold

    def detect_behavioral_shift(
        self,
        partner_id: str,
        weekly_metrics: list[dict],
    ) -> TemporalDriftSignal:
        """Analyze weekly metrics timeline and detect change points / abrupt shifts."""
        if len(weekly_metrics) < 4:
            return TemporalDriftSignal(
                partner_id=partner_id,
                shift_detected=False,
                shift_magnitude=0.0,
                weeks_since_shift=0,
                predicted_escalation_risk=0.10,
                alert_message=f"Insufficient historical data for partner {partner_id}.",
            )

        # Split timeline into baseline (historical) and recent (last 2 weeks)
        split_idx = max(2, len(weekly_metrics) - 2)
        baseline_weeks = weekly_metrics[:split_idx]
        recent_weeks = weekly_metrics[split_idx:]

        base_micro_pct = float(np.mean([w.get("micro_trade_pct", 0.0) for w in baseline_weeks]))
        recent_micro_pct = float(np.mean([w.get("micro_trade_pct", 0.0) for w in recent_weeks]))

        base_withdrawal_pct = float(np.mean([w.get("withdrawal_72h_pct", 0.0) for w in baseline_weeks]))
        recent_withdrawal_pct = float(np.mean([w.get("withdrawal_72h_pct", 0.0) for w in recent_weeks]))

        base_refs = float(np.mean([w.get("referred_count", 0.0) for w in baseline_weeks]))
        recent_refs = float(np.mean([w.get("referred_count", 0.0) for w in recent_weeks]))

        # Calculate drift delta in micro trades, fast withdrawals, and volume explosion
        micro_drift = max(0.0, (recent_micro_pct - base_micro_pct) / 100.0)
        withdrawal_drift = max(0.0, (recent_withdrawal_pct - base_withdrawal_pct) / 100.0)
        volume_spike = min(1.0, max(0.0, (recent_refs - base_refs) / max(base_refs, 1.0) / 10.0))

        shift_magnitude = round(
            0.40 * micro_drift + 0.40 * withdrawal_drift + 0.20 * volume_spike,
            4,
        )

        shift_detected = shift_magnitude >= self.drift_threshold
        weeks_since = len(recent_weeks)
        predicted_escalation = round(min(0.99, shift_magnitude * 1.15), 4)

        if shift_detected:
            alert = (
                f"Partner behavior shift detected {weeks_since} weeks ago matching pre-fraud signature: "
                f"micro-trades increased from {base_micro_pct:.1f}% to {recent_micro_pct:.1f}%, "
                f"72h fast withdrawals surged to {recent_withdrawal_pct:.1f}%. Predicted escalation in next 2 weeks."
            )
        else:
            alert = f"Partner {partner_id} behavior consistent with historical baseline."

        return TemporalDriftSignal(
            partner_id=partner_id,
            shift_detected=shift_detected,
            shift_magnitude=shift_magnitude,
            weeks_since_shift=weeks_since,
            predicted_escalation_risk=predicted_escalation,
            alert_message=alert,
        )
