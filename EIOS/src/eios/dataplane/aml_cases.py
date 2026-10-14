"""From scored alerts to investigation cases: one case per client, ranked (spec 031 FR-005)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from eios.aml.models import AMLAlert, AMLPriorityTier, AMLTypology, MuleRingCluster

TOP_K = 50
MIN_TOP_RISK = 0.60  # the triage scorer's own threshold for a prioritised case
STATUS_UNREVIEWED = "UNREVIEWED"


@dataclass(frozen=True)
class AmlCase:
    """A client under review: the strongest alert's risk, everything that fired, and the ring if any."""

    client_id: str
    alert_id: str
    risk: float
    tier: AMLPriorityTier
    typology: AMLTypology
    rules: tuple[str, ...]
    reasons: tuple[str, ...]
    alert_count: int
    ring_id: str | None
    ring_size: int
    members: tuple[str, ...]
    triggered_at: datetime
    rank: int
    in_top_k: bool
    status: str = STATUS_UNREVIEWED


def case_alert_id(client_id: str) -> str:
    return f"ALT-{client_id}"


def build_cases(
    alerts: list[AMLAlert], clusters: list[MuleRingCluster], first_move: Mapping[str, datetime]
) -> tuple[AmlCase, ...]:
    """One case per ring and one per client outside any ring, ranked by the strongest alert in it.

    An investigator works a ring as a single case, so 23 mules take one slot of the fifty, not twenty-three. The
    lead account is the ring's first mover (earliest deposit); every member stays reachable by its own id.
    """
    ring_of = {m: c for c in clusters if c.is_syndicate for m in c.member_client_ids}
    groups: dict[str, list[AMLAlert]] = {}
    for alert in alerts:
        ring = ring_of.get(alert.client_id)
        groups.setdefault(ring.cluster_id if ring else alert.client_id, []).append(alert)
    ranked = sorted(groups.items(), key=lambda item: _strength(item[1]) + (item[0],))
    by_ring = {c.cluster_id: c for c in clusters if c.is_syndicate}
    return tuple(
        _case(found, by_ring.get(key), rank, first_move)
        for rank, (key, found) in enumerate(ranked, start=1)
    )


def _strength(found: list[AMLAlert]) -> tuple[float, float]:
    return (-max(a.risk_score for a in found), -max(a.amount_usd for a in found))


def _case(
    found: list[AMLAlert],
    ring: MuleRingCluster | None,
    rank: int,
    first_move: Mapping[str, datetime],
) -> AmlCase:
    top = max(found, key=lambda a: (a.risk_score, a.amount_usd))
    lead = _lead(top.client_id, ring, first_move)
    ordered = sorted(found, key=lambda a: -a.risk_score)
    rules = tuple(dict.fromkeys(str(a.attributes.get("rule", "")) for a in ordered))
    reasons = tuple(dict.fromkeys(str(a.attributes.get("detail", "")) for a in ordered))
    members = tuple(ring.member_client_ids) if ring else (top.client_id,)
    return AmlCase(
        client_id=lead,
        alert_id=case_alert_id(lead),
        risk=top.risk_score,
        tier=top.priority_tier,
        typology=top.typology,
        rules=rules,
        reasons=reasons,
        alert_count=len(found),
        ring_id=ring.cluster_id if ring else None,
        ring_size=ring.cluster_size if ring else 1,
        members=members,
        triggered_at=top.triggered_at,
        rank=rank,
        in_top_k=rank <= TOP_K and top.risk_score >= MIN_TOP_RISK,
    )


def _lead(strongest: str, ring: MuleRingCluster | None, first_move: Mapping[str, datetime]) -> str:
    """The first mover of a ring; a lone client leads their own case."""
    if ring is None:
        return strongest
    return min(
        ring.member_client_ids,
        key=lambda c: (first_move.get(c, datetime.max.replace(tzinfo=None)), c),
    )
