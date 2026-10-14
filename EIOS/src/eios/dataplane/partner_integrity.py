"""Integrity evidence for a partner: opposite-trading pairs across its network and AML cases among its referrals.

Pairs come from `TimeBucketedPairDetector` over the referred-account trades; AML exposure from the AML engine's
cases, matched by the partner each client names at sign-up. An empty result means the detector ran over this
partner's trades and found nothing, which is reported as such.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from eios.dataplane.aml_engine import AmlSnapshot
from eios.dataplane.partner_engine import PartnerSnapshot
from eios.fraud.models import TradingPairCorrelation

STATEMENT = "Observed patterns only; they are not a finding about the partner's intent."


@dataclass(frozen=True)
class PairExposure:
    pairs: tuple[TradingPairCorrelation, ...]
    max_confidence: float
    commission_usd: float


def pair_exposure(snap: PartnerSnapshot, partners: set[str]) -> PairExposure:
    pairs = tuple(p for p in snap.pairs if p.partner_a in partners or p.partner_b in partners)
    return PairExposure(
        pairs=pairs,
        max_confidence=round(max((p.collusion_confidence for p in pairs), default=0.0), 4),
        commission_usd=round(sum(p.total_commission_extracted_usd for p in pairs), 2),
    )


def _median_lag_seconds(trades: pd.DataFrame, a: str, b: str) -> float:
    """Median gap between each of A's trades and B's nearest opposite trade."""
    left = trades[trades["account_id"] == a][["timestamp"]].sort_values("timestamp")
    right = (
        trades[trades["account_id"] == b][["timestamp"]]
        .sort_values("timestamp")
        .rename(columns={"timestamp": "t_b"})
    )
    if left.empty or right.empty:
        return 0.0
    joined = pd.merge_asof(left, right, left_on="timestamp", right_on="t_b", direction="nearest")
    return round(float((joined["t_b"] - joined["timestamp"]).abs().dt.total_seconds().median()), 2)


def _ring(snap: PartnerSnapshot, p: TradingPairCorrelation) -> dict[str, Any]:
    return {
        "ring_id": p.pair_id,
        "scheme": f"Opposite trading on {p.symbol}",
        "paired_accounts": [p.account_a, p.account_b],
        "partners": [p.partner_a, p.partner_b],
        "matched_timing_seconds": _median_lag_seconds(snap.world.trades, p.account_a, p.account_b),
        "unearned_commission_liability_usd": p.total_commission_extracted_usd,
        "co_occurrences": p.co_occurrence_count,
        "collusion_confidence": p.collusion_confidence,
    }


def _referred(aml: AmlSnapshot | None, pid: str) -> list[str] | None:
    if aml is None:
        return None
    clients = aml.world.clients
    return [str(c) for c in clients.loc[clients["partner_id"] == pid, "client_id"]]


def _aml_exposure(aml: AmlSnapshot | None, referred: list[str] | None) -> list[dict[str, Any]]:
    if aml is None or not referred:
        return []
    mine = set(referred)
    return [
        {
            "alert_id": c.alert_id,
            "entity_id": c.client_id,
            "ring_size": c.ring_size,
            "referred_members": len(mine & set(c.members)),
            "risk_score": round(c.risk * 100),
            "typology": c.typology.value,
        }
        for c in aml.cases
        if c.in_top_k and mine & set(c.members)
    ]


def _sub_affiliate(snap: PartnerSnapshot, kid: str, exposure: PairExposure) -> dict[str, Any]:
    roster = snap.world.roster.set_index("partner_id")
    row = snap.scored.loc[kid]
    own = [p for p in exposure.pairs if kid in (p.partner_a, p.partner_b)]
    return {
        "id": kid,
        "name": str(roster.loc[kid, "name"]),
        "tier": str(roster.loc[kid, "tier"]),
        "volume_usd": round(float(row["realized_volume_30d_usd"]), 2),
        "churn_hazard_probability": round(float(row["hazard_probability_30d"]), 4),
        "co_occurrence_pct": round(
            max((p.collusion_confidence for p in own), default=0.0) * 100.0, 1
        ),
        "flagged_mirror_trading": bool(own),
    }


def referral_tree(
    snap: PartnerSnapshot, aml: AmlSnapshot | None, pid: str, children: set[str]
) -> dict[str, Any]:
    roster = snap.world.roster.set_index("partner_id")
    exposure = pair_exposure(snap, children | {pid})
    referred = _referred(aml, pid)
    active = [k for k in children if float(snap.scored.loc[k, "logins_recent"]) > 0]
    return {
        "master_partner_id": pid,
        "name": str(roster.loc[pid, "name"]),
        "tier": str(roster.loc[pid, "tier"]),
        "active_sub_affiliates_count": len(active),
        "referred_client_count": len(referred) if referred is not None else 0,
        "detected_abusive_rings": [_ring(snap, p) for p in exposure.pairs],
        "sub_affiliates": [_sub_affiliate(snap, k, exposure) for k in sorted(children)],
        "aml_exposure": _aml_exposure(aml, referred),
        "statement": STATEMENT,
    }
