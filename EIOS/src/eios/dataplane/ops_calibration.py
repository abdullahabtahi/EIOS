"""How well last month's churn hazards predicted what the partners then did (spec 035).

The partner engine scored every partner thirty days before the cut. Here each of those hazards is set against what is
observable now: did the partner's 30-day volume fall by 15% or more from when it was scored. Nothing reads the planted
truth; the label is the partner's own behaviour. [ASSUMPTION] a fall of 15% or more is what churn means for a referral
partner here. The threshold is a parameter, not a finding, and the verdict does not depend on it: see
`docs/operations-engine.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

from eios.dataplane.partner_engine import PartnerSnapshot

LOOKBACK_DAYS = 30
CHURN_VOLUME_RATIO = 0.85


@dataclass(frozen=True)
class CalibrationSample:
    model_id: str
    probabilities: tuple[float, ...]
    labels: tuple[int, ...]
    basis: str


def calibration_sample(snapshot: PartnerSnapshot) -> CalibrationSample | None:
    then = snapshot.history.get(LOOKBACK_DAYS)
    if then is None:
        return None
    now = snapshot.scored["realized_volume_30d_usd"]
    joined = then.join(now, how="inner").query("value_at_risk > 0")
    if joined.empty:
        return None
    churned = joined["realized_volume_30d_usd"] <= CHURN_VOLUME_RATIO * joined["value_at_risk"]
    return CalibrationSample(
        model_id="churn-hazard-30d",
        probabilities=tuple(float(p) for p in joined["hazard_probability_30d"]),
        labels=tuple(int(c) for c in churned),
        basis=(
            f"hazards scored {LOOKBACK_DAYS} days before the cut against whether 30-day volume has since "
            f"fallen to {CHURN_VOLUME_RATIO:.0%} or less"
        ),
    )
