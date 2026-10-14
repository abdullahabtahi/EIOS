"""Run the partner engines over the seeded world (spec 032 FR-004 to FR-006).

The world is loaded into DuckDB hot state as the L1 data products the churn pipeline reads, cut at the scoring
date so no run sees the future. `ChurnRadarPipeline` scores hazard (seasonality filter, discrete-time hazard model,
cohort test) at as-of, 14 and 30 days earlier; `ChurnSignalExplainer` attributes each partner's risk to signal
families; `TimeBucketedPairDetector` looks for opposite trading across referred accounts. Quality against the
planted truth is measured here and logged; nothing downstream reads the truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from eios.churn.explainer import ChurnSignalExplainer
from eios.churn.models import CohortAnomalyAlert, SignalContribution
from eios.churn.pipeline import ChurnRadarPipeline
from eios.foundry.scenarios.partner_world import PartnerWorld
from eios.fraud.models import TradingPairCorrelation
from eios.fraud.pair_detector import TimeBucketedPairDetector
from eios.ingestion.hot_state import HotStateEngine

HISTORY_OFFSETS = (14, 30)  # days before as-of at which the radar is re-scored for drift
HIGH_RISK = 0.5
VOLUME_DAYS = 30


@dataclass(frozen=True)
class PartnerQuality:
    """How well the engines recover the planted truth. [MEASURED] on every build."""

    partners: int
    planted_churners: int
    hazard_auc: float
    precision_at_k: float  # top-k by hazard, k = number of planted churners
    seasonal_false_alarms: int  # holiday dips scored high risk
    seasonal_partners: int
    cohort_found: bool
    false_cohorts: int
    pairs_found: int
    pairs_planted: int
    false_pairs: int


@dataclass(frozen=True)
class PartnerSnapshot:
    world: PartnerWorld
    scored: pd.DataFrame  # as-of features and scores, indexed by partner_id
    history: dict[int, pd.DataFrame]  # days back -> hazard and value at that date
    contributions: dict[str, tuple[SignalContribution, ...]]
    cohorts: tuple[CohortAnomalyAlert, ...]
    pairs: tuple[TradingPairCorrelation, ...]
    quality: PartnerQuality

    @property
    def as_of(self) -> date:
        return self.world.config.as_of.date()


def _volume(world: PartnerWorld, cutoff: date) -> pd.Series:
    window = world.days[
        (world.days["date"] <= cutoff) & (world.days["date"] > cutoff - timedelta(days=VOLUME_DAYS))
    ]
    return window.groupby("partner_id")["volume_usd"].sum().round(2)


def _load(world: PartnerWorld, cutoff: date) -> HotStateEngine:
    """Hot state holding the world as it was at the end of `cutoff`."""
    hs = HotStateEngine()
    cur = hs.get_cursor()
    volume = _volume(world, cutoff)
    p360 = world.roster.assign(
        value_at_risk=world.roster["partner_id"].map(volume).fillna(0.0),
        manager_id="",
        status="ACTIVE",
    )[["partner_id", "tier", "region", "tenure_months", "value_at_risk", "manager_id", "status"]]
    days = world.days[world.days["date"] <= cutoff][
        ["partner_id", "date", "logins", "referrals", "ftd_count", "conversion_rate", "clicks"]
    ]
    end = pd.Timestamp(cutoff + timedelta(days=1))  # world timestamps are naive UTC
    comms = world.messages[world.messages["timestamp"] < end][
        ["message_id", "partner_id", "channel", "sentiment", "text", "timestamp"]
    ]
    paid = world.commissions[world.commissions["paid_at"] < end]
    for table, frame in (
        ("partner_360", p360),
        ("partner_engagement_signals", days),
        ("partner_comms", comms),
        ("commission_ledger", paid),
    ):
        cur.register("_frame", frame)
        cur.execute(f"INSERT INTO {table} SELECT * FROM _frame")  # noqa: S608
        cur.unregister("_frame")
    return hs


def _score(world: PartnerWorld, cutoff: date) -> tuple[pd.DataFrame, list[CohortAnomalyAlert]]:
    hs = _load(world, cutoff)
    pipeline = ChurnRadarPipeline(hot_state=hs)
    scored = pipeline.run_scoring_job(as_of_date=cutoff).set_index("partner_id")
    alerts = pipeline.cohort_detector.detect_cohort_anomalies(as_of_date=cutoff)
    hs.close()
    return scored, alerts


def _auc(scores: pd.Series, positives: frozenset[str]) -> float:
    """Probability a planted churner outranks a non-churner (Mann-Whitney)."""
    ranks = scores.rank()
    is_pos = scores.index.isin(list(positives))
    n_pos, n_neg = int(is_pos.sum()), int((~is_pos).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.0
    return float((ranks[is_pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _quality(
    world: PartnerWorld,
    scored: pd.DataFrame,
    cohorts: list[CohortAnomalyAlert],
    pairs: list[TradingPairCorrelation],
) -> PartnerQuality:
    truth = world.truth
    hazard = scored["hazard_probability_30d"]
    churners = truth.churners()
    top = set(hazard.sort_values(ascending=False).index[: len(churners)])
    seasonal = truth.seasonal()
    cohort_region = world.config.cohort_region
    planted = {tuple(sorted((p.account_a, p.account_b))) for p in truth.pairs}
    found = {tuple(sorted((p.account_a, p.account_b))) for p in pairs}
    return PartnerQuality(
        partners=len(scored),
        planted_churners=len(churners),
        hazard_auc=round(_auc(hazard, churners), 3),
        precision_at_k=round(len(top & churners) / max(len(churners), 1), 3),
        seasonal_false_alarms=int(sum(hazard.get(p, 0.0) >= HIGH_RISK for p in seasonal)),
        seasonal_partners=len(seasonal),
        cohort_found=any(a.region_id == cohort_region for a in cohorts),
        false_cohorts=sum(a.region_id != cohort_region for a in cohorts),
        pairs_found=len(found & planted),
        pairs_planted=len(planted),
        false_pairs=len(found - planted),
    )


def _contributions(scored: pd.DataFrame) -> dict[str, tuple[SignalContribution, ...]]:
    explainer = ChurnSignalExplainer()
    return {str(pid): tuple(explainer.compute_contributions(row)) for pid, row in scored.iterrows()}


def run_partner_engine(world: PartnerWorld) -> PartnerSnapshot:
    as_of = world.config.as_of.date()
    scored, cohorts = _score(world, as_of)
    scored = scored.assign(realized_volume_30d_usd=scored["value_at_risk"])
    history = {}
    for back in HISTORY_OFFSETS:
        past, _ = _score(world, as_of - timedelta(days=back))
        history[back] = past[["hazard_probability_30d", "value_at_risk"]]
    pairs = TimeBucketedPairDetector().detect_pairs(world.trades)
    return PartnerSnapshot(
        world=world,
        scored=scored,
        history=history,
        contributions=_contributions(scored),
        cohorts=tuple(cohorts),
        pairs=tuple(pairs),
        quality=_quality(world, scored, cohorts, pairs),
    )


def expected_days_to_churn(hazard_30d: float) -> int:
    """Days until survival falls to one half under the scored weekly hazard; capped at a year."""
    weekly = 1.0 - (1.0 - min(max(hazard_30d, 1e-6), 0.999999)) ** 0.25
    days = 7.0 * np.log(0.5) / np.log(1.0 - weekly)
    return int(min(max(round(days), 1), 365))
