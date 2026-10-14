"""Run the real AML detectors and the triage scorer over a world; measure them against the truth (spec 031).

`run_aml_engine` is the whole pipeline: facts, peer baselines, round-trip, mule ring and rule alerts, calibrated
triage, one ranked case per client, and quality metrics against what was planted. Nothing reads the truth until
the last step, and only to score the detectors.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd

from eios.aml.models import AMLAlert, MuleRingCluster
from eios.aml.triage_scorer import AlertTriageScorer
from eios.dataplane import aml_signals as sig
from eios.dataplane.aml_cases import TOP_K, AmlCase, build_cases
from eios.dataplane.aml_causal import ring_refutation
from eios.dataplane.aml_facts import client_facts, deposit_baseline, volume_baseline
from eios.foundry.scenarios.aml_world import AmlWorld
from eios.synthesis.models import RefutationReport


@dataclass(frozen=True)
class AmlQuality:
    """How well the detectors did against the planted truth `[MEASURED]`."""

    raw_alerts: int
    cases: int
    top_k: int
    planted_cases: int
    hits_at_k: int
    precision_at_k: float
    recall_at_k: float
    recall_any_alert: float
    ring_recovery: float
    largest_cluster: int
    build_seconds: float


@dataclass(frozen=True)
class AmlSnapshot:
    world: AmlWorld
    facts: pd.DataFrame
    clusters: tuple[MuleRingCluster, ...]
    alerts: tuple[AMLAlert, ...]
    cases: tuple[AmlCase, ...]
    quality: AmlQuality
    ring_refutation: RefutationReport

    def case_for(self, client_id: str) -> AmlCase | None:
        """The case a client is worked in: its own, or its ring's."""
        return next((c for c in self.cases if client_id in c.members), None)

    def ring_of(self, client_id: str) -> MuleRingCluster | None:
        return next(
            (c for c in self.clusters if c.is_syndicate and client_id in c.member_client_ids), None
        )


def run_aml_engine(world: AmlWorld, rules: sig.RuleThresholds | None = None) -> AmlSnapshot:
    started = time.perf_counter()
    rules = rules or sig.RuleThresholds()
    facts = client_facts(world)
    volume, deposits = volume_baseline(facts), deposit_baseline(world)
    clusters = sig.detect_clusters(world)
    raw = [
        *sig.rule_alerts(world, facts, volume, rules),
        *sig.new_account_alerts(world, facts, volume, rules),
        *sig.large_deposit_alerts(world, facts, rules),
        *sig.round_trip_alerts(world, facts, deposits),
        *sig.mule_alerts(world, facts, clusters, volume),
    ]
    scored = _score(raw)
    first_move = {
        str(c): pd.Timestamp(t).to_pydatetime() for c, t in facts["first_dep"].dropna().items()
    }
    cases = build_cases(scored, clusters, first_move)
    quality = _quality(world, raw, cases, clusters, time.perf_counter() - started)
    refutation = ring_refutation(facts, clusters)
    return AmlSnapshot(world, facts, tuple(clusters), tuple(scored), cases, quality, refutation)


def _score(alerts: list[AMLAlert]) -> list[AMLAlert]:
    """Calibrated triage; the strongest alert wins when the same rule fires twice for one client."""
    scored = AlertTriageScorer().score_queue(alerts)
    best: dict[str, AMLAlert] = {}
    for alert in scored:
        kept = best.get(alert.alert_id)
        if kept is None or alert.risk_score > kept.risk_score:
            best[alert.alert_id] = alert
    return list(best.values())


def _quality(
    world: AmlWorld,
    raw: list[AMLAlert],
    cases: tuple[AmlCase, ...],
    clusters: list[MuleRingCluster],
    seconds: float,
) -> AmlQuality:
    bad = world.truth.malicious()
    top = [c for c in cases if c.in_top_k]
    flagged = {a.client_id for a in raw}
    covered = {m for c in top for m in c.members}
    hits = sum(1 for c in top if bad & set(c.members))
    syndicates = [c for c in clusters if c.is_syndicate]
    return AmlQuality(
        raw_alerts=len(raw),
        cases=len(cases),
        top_k=len(top),
        planted_cases=sum(1 for c in cases if bad & set(c.members)),
        hits_at_k=hits,
        precision_at_k=round(hits / len(top), 4) if top else 0.0,
        recall_at_k=round(len(bad & covered) / len(bad), 4) if bad else 0.0,
        recall_any_alert=round(len(bad & flagged) / len(bad), 4) if bad else 0.0,
        ring_recovery=_ring_recovery(world, syndicates),
        largest_cluster=max((c.cluster_size for c in syndicates), default=0),
        build_seconds=round(seconds, 2),
    )


def _ring_recovery(world: AmlWorld, syndicates: list[MuleRingCluster]) -> float:
    """Mean over planted rings of the share of members that landed together in one detected cluster."""
    shares = []
    for members in world.truth.rings.values():
        best = max((len(set(members) & set(c.member_client_ids)) for c in syndicates), default=0)
        shares.append(best / len(members))
    return round(sum(shares) / len(shares), 4) if shares else 0.0


__all__ = ["TOP_K", "AmlQuality", "AmlSnapshot", "run_aml_engine"]
