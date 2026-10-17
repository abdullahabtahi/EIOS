"""How early the churn radar sees planted churn: the radar's quality at several leads, not only today.

The brief asks for disengagement caught "well before churn occurs, with enough lead time for effective intervention" and
for few false alarms. A single AUC at the cut cannot say that. Here the hazards the engine scored `lead` days before the
cut are ranked against the planted churners, and the alerts (hazard at or above the high-risk line) are counted, so the
alert volume and its precision are visible at each lead. The truth table is read by this evaluation only, never by an engine.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from eios.dataplane.partner_engine import HIGH_RISK, PartnerSnapshot
from eios.dataplane.rank_metrics import ranking_auc

LEADS = (
    0,
    14,
    30,
)  # days before the cut at which the radar's hazards are read; 0 is the cut itself


@dataclass(frozen=True)
class LeadTimeRow:
    lead_days: int
    planted_churners: int
    auc: float
    precision_at_k: float  # top-k by hazard, k = number of planted churners
    alerts: int  # partners at or above the high-risk line
    alert_precision: float | None  # None when there are no alerts: nothing measured, not zero
    alert_recall: float


def _hazards(snapshot: PartnerSnapshot, lead_days: int) -> pd.Series:
    frame = snapshot.scored if lead_days == 0 else snapshot.history[lead_days]
    return frame["hazard_probability_30d"]


def _row(hazard: pd.Series, churners: frozenset[str], lead_days: int) -> LeadTimeRow:
    top = set(hazard.sort_values(ascending=False).index[: len(churners)])
    alerted = set(hazard.index[hazard >= HIGH_RISK])
    caught = len(alerted & churners)
    return LeadTimeRow(
        lead_days=lead_days,
        planted_churners=len(churners),
        auc=round(ranking_auc(hazard, churners), 3),
        precision_at_k=round(len(top & churners) / max(len(churners), 1), 3),
        alerts=len(alerted),
        alert_precision=round(caught / len(alerted), 3) if alerted else None,
        alert_recall=round(caught / max(len(churners), 1), 3),
    )


def lead_time_report(snapshot: PartnerSnapshot) -> tuple[LeadTimeRow, ...]:
    """One row per lead, today first. [MEASURED] against what the world planted."""
    churners = snapshot.world.truth.churners()
    return tuple(_row(_hazards(snapshot, lead), churners, lead) for lead in LEADS)
