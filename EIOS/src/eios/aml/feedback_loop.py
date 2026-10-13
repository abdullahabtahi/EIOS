"""Analyst Investigation Decision Feedback Loop & Threshold Recalibration (US7 / P3).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- specs/010-client-aml/spec.md (User Story 7, FR-015, SC-001, SC-003)
- .specify/memory/constitution.md (Principles I, VI)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from eios.aml.triage_scorer import AlertTriageScorer


@dataclass
class AnalystDisposition:
    alert_id: str
    client_id: str
    risk_score: float
    disposition: str  # "CONFIRMED_SAR" | "DISMISSED_FALSE_POSITIVE"
    analyst_id: str
    timestamp: datetime | None = None


class AnalystFeedbackLoop:
    """Ingests human investigation dispositions and dynamically recalibrates triage thresholds."""

    def __init__(self, initial_threshold: float = 0.75) -> None:
        self.initial_threshold = float(initial_threshold)
        self.current_threshold = float(initial_threshold)
        self.disposition_history: list[AnalystDisposition] = []

    def process_disposition_batch(
        self,
        dispositions: list[AnalystDisposition],
    ) -> dict[str, Any]:
        """Ingest labeled batch of analyst investigation decisions and adapt thresholds."""
        if not dispositions:
            return {
                "processed_count": 0,
                "confirmed_sars": 0,
                "dismissed_false_positives": 0,
                "initial_threshold": self.current_threshold,
                "new_threshold": self.current_threshold,
                "recalibrated": False,
            }

        self.disposition_history.extend(dispositions)

        confirmed = [d for d in dispositions if d.disposition == "CONFIRMED_SAR"]
        dismissed = [d for d in dispositions if d.disposition == "DISMISSED_FALSE_POSITIVE"]

        conf_count = len(confirmed)
        dism_count = len(dismissed)
        total_count = len(dispositions)

        prev_thresh = self.current_threshold

        # Recalibration logic:
        # If false positive rate is high (> 50%), raise threshold to eliminate borderline noise
        # while keeping the vast majority of confirmed SARs
        if total_count > 0 and dism_count / total_count > 0.50:
            # Find the max score among lower 75% of dismissed false alarms
            dism_scores = sorted([d.risk_score for d in dismissed])
            cutoff_idx = int(0.75 * len(dism_scores))
            suggested_thresh = dism_scores[cutoff_idx] if dism_scores else prev_thresh

            # Ensure we don't cut off confirmed SARs (threshold <= min(confirmed scores) + margin)
            if confirmed:
                min_conf = min(d.risk_score for d in confirmed)
                suggested_thresh = min(suggested_thresh, min_conf)

            # Smooth threshold adjustment with damping
            new_thresh = min(0.90, max(prev_thresh + 0.02, suggested_thresh))
        else:
            new_thresh = prev_thresh

        self.current_threshold = round(new_thresh, 4)

        return {
            "processed_count": total_count,
            "confirmed_sars": conf_count,
            "dismissed_false_positives": dism_count,
            "initial_threshold": prev_thresh,
            "new_threshold": self.current_threshold,
            "recalibrated": True,
        }

    def apply_to_scorer(self, scorer: AlertTriageScorer) -> None:
        """Update triage scorer operational threshold with recalibrated baseline."""
        scorer.min_score_threshold = self.current_threshold
