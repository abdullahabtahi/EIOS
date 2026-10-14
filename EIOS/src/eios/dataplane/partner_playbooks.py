"""Retention playbooks for a partner, priced from its own volume and scored by the hazard model's counterfactual.

A playbook names the signal it acts on. Its projected uplift is the drop in the scored 30-day hazard when those
features are moved as the playbook intends, re-scored by the same `DiscreteTimeHazardModel`. That is a model
projection under the hazard model, not a causal estimate: no refuter has tested it (RL-3), and the label says so.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from eios.churn.hazard_model import DiscreteTimeHazardModel
from eios.cockpit.partner import RetentionPlaybookDeal
from eios.dataplane.partner_evidence import DriverCode, PartnerEvidence

FAST_PATH_BUDGET_USD = 2500.0  # single-approver ceiling (governance policy)
HORIZON_MONTHS = 3  # [ASSUMPTION] a concession runs for a quarter
NET_REVENUE_RATE = 0.035  # [ASSUMPTION] broker net revenue per dollar of referred deposit volume
PROJECTION_BASIS = "Model projection under the hazard model; not a causal estimate"
_FEATURES = (
    "login_velocity_decay_3w",
    "sentiment_negative_ratio",
    "commission_velocity_30d",
    "competitor_mention_flag",
)

Shift = Callable[[pd.Series], dict[str, float]]


@dataclass(frozen=True)
class Playbook:
    playbook_id: str
    title: str
    action_type: str
    cost: Callable[[pd.Series], float]  # USD, from the partner's scored row
    shift: Shift  # the feature values the playbook aims for


def _volume(row: pd.Series) -> float:
    return float(row["realized_volume_30d_usd"])


PLAYBOOKS: dict[str, Playbook] = {
    "cashier_rail": Playbook(
        "pb_cashier_rail",
        "Whitelist a direct cashier rail",
        "WhitelistDirectCashierRail",
        lambda _r: 0.0,
        lambda r: {
            "sentiment_negative_ratio": 0.3 * r["sentiment_negative_ratio"],
            "login_velocity_decay_3w": 0.5 * r["login_velocity_decay_3w"],
        },
    ),
    "spread_rebate": Playbook(
        "pb_spread_rebate",
        "Spread rebate concession for 90 days",
        "DeployRetentionConcession",
        lambda r: round(
            0.012 * HORIZON_MONTHS * _volume(r), -1
        ),  # [ASSUMPTION] 1.2% of quarterly volume
        lambda r: {
            "competitor_mention_flag": 0.0,
            "sentiment_negative_ratio": 0.5 * r["sentiment_negative_ratio"],
            "login_velocity_decay_3w": 0.6 * r["login_velocity_decay_3w"],
        },
    ),
    "rebate_reconcile": Playbook(
        "pb_rebate_reconcile",
        "Reconcile the rebate and restore the agreed rate",
        "DeployRetentionConcession",
        lambda r: round(max(float(r["comm_prior"]) - float(r["comm_recent"]), 0.0), -1),
        lambda r: {
            "commission_velocity_30d": 0.0,
            "sentiment_negative_ratio": 0.4 * r["sentiment_negative_ratio"],
        },
    ),
    "co_marketing": Playbook(
        "pb_co_marketing",
        "Co-marketing budget to re-engage the partner's audience",
        "AllocateCoMarketingBudget",
        lambda r: round(
            0.005 * HORIZON_MONTHS * _volume(r), -1
        ),  # [ASSUMPTION] 0.5% of quarterly volume
        lambda r: {"login_velocity_decay_3w": 0.6 * r["login_velocity_decay_3w"]},
    ),
}
_BY_DRIVER = {
    DriverCode.CASHIER: ("cashier_rail", "spread_rebate"),
    DriverCode.POACHING: ("spread_rebate", "co_marketing"),
    DriverCode.REBATE: ("rebate_reconcile", "spread_rebate"),
    DriverCode.DECAY: ("co_marketing", "spread_rebate"),
}


@dataclass(frozen=True)
class Projection:
    hazard_now: float
    hazard_after: float
    uplift_pct: float  # relative drop in hazard
    cost_usd: float
    net_margin_usd: float


class Counterfactual:
    """Re-scores a partner's row with shifted features through the same hazard model the radar uses."""

    def __init__(self) -> None:
        self._model = DiscreteTimeHazardModel()

    def hazard(self, row: pd.Series, overrides: dict[str, float]) -> float:
        frame = pd.DataFrame(
            [
                {
                    **{f: float(row[f]) for f in _FEATURES},
                    **overrides,
                    "seasonal_dip_flag": bool(row.get("seasonal_dip_flag", False)),
                }
            ]
        )
        return float(self._model.predict_30d_hazard(frame)["hazard_probability_30d"].iloc[0])

    def project(self, row: pd.Series, playbook: Playbook, intensity: float = 1.0) -> Projection:
        now = float(row["hazard_probability_30d"])
        target = playbook.shift(row)
        blended = {f: float(row[f]) + (v - float(row[f])) * intensity for f, v in target.items()}
        after = min(self.hazard(row, blended), now)
        cost = round(playbook.cost(row) * intensity, 2)
        saved = (now - after) * _volume(row) * HORIZON_MONTHS * NET_REVENUE_RATE
        return Projection(
            hazard_now=round(now, 4),
            hazard_after=round(after, 4),
            uplift_pct=round((now - after) / now * 100.0, 1) if now > 0 else 0.0,
            cost_usd=cost,
            net_margin_usd=round(saved - cost, 2),
        )


def playbooks_for(evidence: PartnerEvidence) -> tuple[Playbook, ...]:
    return tuple(PLAYBOOKS[k] for k in _BY_DRIVER.get(evidence.driver, ()))


def deals(
    partner_id: str, row: pd.Series, evidence: PartnerEvidence, cf: Counterfactual
) -> list[RetentionPlaybookDeal]:
    out: list[RetentionPlaybookDeal] = []
    for pb in playbooks_for(evidence):
        p = cf.project(row, pb)
        out.append(
            RetentionPlaybookDeal(
                playbook_id=pb.playbook_id,
                title=pb.title,
                partner_id=partner_id,
                action_type=pb.action_type,
                estimated_cost_usd=p.cost_usd,
                is_fast_path_eligible=p.cost_usd <= FAST_PATH_BUDGET_USD,
                requires_four_eyes=p.cost_usd > FAST_PATH_BUDGET_USD,
                projected_retention_uplift_pct=p.uplift_pct,
            )
        )
    return out
