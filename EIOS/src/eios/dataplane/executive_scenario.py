"""The what-if: shock a driver, propagate it through the fitted causal graph, allocate and defend (spec 034, RL-6).

The shock moves one node of the fitted graph (`ScenarioSimulator` walks it in causal order). The revenue effect is
allocated to regions by the partners' exposure (30-day churn hazard times 30-day volume, from the partner engine),
which is additive, so the shares close to exactly 100.00. Mitigations are the retention playbooks the partner engine
already prices, applied to the most exposed region's most exposed partners; what they recover is capped at the loss.
Everything that does not depend on the shock's size is computed once at build, so a request is arithmetic only and
fits the 200 ms budget with room to spare.
"""

from __future__ import annotations

import itertools
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from eios.dataplane.executive_engine import ExecutiveSnapshot
from eios.dataplane.partner_playbooks import PROJECTION_BASIS, Counterfactual, playbooks_for
from eios.dataplane.partner_service import EnginePartnerService
from eios.foundry.scenarios.executive_world import CHURN, FTD, PAYOUT, REVENUE
from eios.synthesis.attribution import largest_remainder_shares
from eios.synthesis.models import CausalEdge, ScenarioShockSpec
from eios.synthesis.scenario import ScenarioSimulator

SHOCK_NODES: Mapping[str, str] = {"competitor_payout_increase": PAYOUT}
CHAIN = (PAYOUT, CHURN, FTD, REVENUE)
COHORT_SIZE = 10  # [ASSUMPTION] the partners a retention push can realistically reach this quarter
MAX_MITIGATIONS = 3


class UnsupportedShockError(ValueError):
    """The shock names no node with a tested causal path to revenue."""


@dataclass(frozen=True)
class Defence:
    """One playbook applied to the exposed cohort: what it costs and what the hazard model says it keeps."""

    playbook_id: str
    title: str
    action_type: str
    region: str
    partners: int
    cost_usd: float
    margin_usd: float


def _exposure_by_region(scored: pd.DataFrame) -> dict[str, float]:
    exposure = scored["hazard_probability_30d"] * scored["realized_volume_30d_usd"]
    return {str(r): float(v) for r, v in exposure.groupby(scored["region"]).sum().items()}


def _defences(partners: EnginePartnerService, region: str) -> tuple[Defence, ...]:
    scored = partners.snapshot.scored
    in_region = scored[scored["region"] == region]
    exposure = in_region["hazard_probability_30d"] * in_region["realized_volume_30d_usd"]
    cohort = exposure.sort_values(ascending=False).index[:COHORT_SIZE]
    cf: Counterfactual = partners.counterfactual()
    tally: dict[str, dict[str, Any]] = {}
    for pid in cohort:
        row = partners.row(str(pid))
        for pb in playbooks_for(partners.evidence(str(pid))):
            proj = cf.project(row, pb)
            slot = tally.setdefault(
                pb.playbook_id, {"pb": pb, "partners": 0, "cost": 0.0, "margin": 0.0}
            )
            slot["partners"] += 1
            slot["cost"] += proj.cost_usd
            slot["margin"] += proj.net_margin_usd
    return tuple(
        Defence(
            s["pb"].playbook_id,
            s["pb"].title,
            s["pb"].action_type,
            region,
            s["partners"],
            round(s["cost"], 2),
            round(s["margin"], 2),
        )
        for s in tally.values()
    )


def _interval(shock: float, edges: Sequence[CausalEdge]) -> tuple[float, float]:
    """Bounds on the end effect when each edge sits anywhere in its own 95% interval (the products of the bounds)."""
    ends = [
        shock * _product(combo)
        for combo in itertools.product(*[(e.ci_lower, e.ci_upper) for e in edges])
    ]
    return min(ends), max(ends)


def _product(values: Sequence[float]) -> float:
    out = 1.0
    for v in values:
        out *= v
    return out


class WhatIfEngine:
    def __init__(self, snapshot: ExecutiveSnapshot, partners: EnginePartnerService) -> None:
        self._snap = snapshot
        self._sim = ScenarioSimulator(snapshot.fit.cache.dag)
        by_edge = {(e.source_metric, e.target_metric): e for e in snapshot.fit.manifest.edges}
        self._path = tuple(by_edge.get(pair) for pair in itertools.pairwise(CHAIN))
        regions = _exposure_by_region(partners.snapshot.scored)
        self._exposure = regions
        self._shares = largest_remainder_shares(regions)
        self._defences = _defences(partners, max(regions, key=lambda r: regions[r]))

    def shock_path(self, shock: str) -> tuple[tuple[str, str], ...]:
        self._node(shock)
        return tuple(itertools.pairwise(CHAIN))

    def _node(self, shock: str) -> str:
        node = SHOCK_NODES.get(shock)
        if node is None:
            raise UnsupportedShockError(
                f"'{shock}' has no tested causal path to revenue; the spread edge failed the causal gate. "
                f"The shock with a tested path is: {', '.join(sorted(SHOCK_NODES))}"
            )
        return node

    def simulate(self, shock: str, magnitude_pct: float) -> dict[str, Any]:
        started = time.perf_counter()
        node = self._node(shock)
        edges = [e for e in self._path if e is not None]
        if len(edges) != len(self._path):
            raise UnsupportedShockError(
                "the fitted graph has no complete path from the shock to revenue"
            )
        latest = self._snap.latest
        step = latest[node] * magnitude_pct / 100.0
        deltas = self._sim.simulate(
            ScenarioShockSpec(scenario_name=shock, shocks={node: step})
        ).propagated_deltas
        revenue = deltas[REVENUE]
        seen = self._snap.world.days[node]
        shocked = latest[node] + step
        extrapolates = bool(shocked < float(seen.min()) or shocked > float(seen.max()))
        low, high = _interval(step, edges)
        out: dict[str, Any] = {
            "shock_param": shock,
            "magnitude_pct": magnitude_pct,
            "projected_changes": {
                "partner_churn_delta_pct": round(deltas[CHURN] * 100.0, 4),
                "first_deposit_delta_pct": round(deltas[FTD] / latest[FTD] * 100.0, 4),
                "projected_revenue_impact_usd": round(revenue, 2),
            },
            "attribution_waterfall": [
                {"driver": f"{region} partners", "contribution_pct": pct}
                for region, pct in self._shares.items()
            ],
            "attribution_sum_pct": round(sum(self._shares.values()), 2),
            "confidence_interval": [round(low, 2), round(high, 2)],
            "mitigations": self._mitigations(-revenue),
            "mitigation_basis": PROJECTION_BASIS,
            "extrapolates_beyond_history": extrapolates,
        }
        out["latency_ms"] = round(
            (time.perf_counter() - started) * 1000.0, 2
        )  # the whole request (RL-6)
        return out

    def _mitigations(self, loss_usd: float) -> list[dict[str, Any]]:
        if loss_usd <= 0:
            return []
        worth = [d for d in self._defences if d.margin_usd > 0]
        ranked = sorted(worth, key=lambda d: d.margin_usd, reverse=True)[:MAX_MITIGATIONS]
        return [
            {
                "playbook_id": d.playbook_id,
                "title": d.title,
                "action_type": d.action_type,
                "target_region": d.region,
                "partners": d.partners,
                "estimated_cost_usd": d.cost_usd,
                "projected_margin_kept_usd": round(min(d.margin_usd, loss_usd), 2),
            }
            for d in ranked
        ]
