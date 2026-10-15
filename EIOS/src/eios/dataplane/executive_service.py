"""The executive read model over the engines (spec 034): briefing, causal graph, forecast and what-if, all computed.

Same public methods as `ExecutiveCockpitService`, so the screen, the API routes and the assistant's tools do not
know which plane they stand on. Origin is `engine`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from eios.cockpit.executive import (
    CausalDAGGraph,
    CausalEdge,
    CausalEdgeRefuterStatus,
    CausalNode,
    ForecastView,
    MorningBriefingDossier,
)
from eios.cockpit.provenance import ProvenanceResolver
from eios.dataplane.aml_engine import AmlSnapshot
from eios.dataplane.executive_briefing import BriefingBuilder
from eios.dataplane.executive_engine import ExecutiveSnapshot
from eios.dataplane.executive_scenario import WhatIfEngine
from eios.dataplane.partner_service import EnginePartnerService
from eios.foundry.scenarios.executive_world import CHURN, FTD, PAYOUT, REVENUE, SPREAD
from eios.ontology.metrics.catalog import create_default_registry
from eios.synthesis.scm_fit import FittedEdge

MIN_CONFIDENCE, MIN_PLACEBO_P = 0.80, 0.05  # constitution RL-3
VERIFIED = "Verified Causal"
UNVERIFIED = "Correlation Detected; Insufficient Evidence"
_NODES = (
    (PAYOUT, "Competitor Payout Rate", "Competitive"),
    (SPREAD, "Average Spread (pips)", "Competitive"),
    (CHURN, "Partner Churn Rate", "Partner"),
    (FTD, "First-Time Deposits (28d)", "Client"),
    (REVENUE, "Net Revenue (USD)", "Financial"),
)


def _verified(e: FittedEdge) -> bool:
    r = e.report
    return (
        e.passed
        and not e.candidate.control
        and e.confidence >= MIN_CONFIDENCE
        and r.placebo_p_value > MIN_PLACEBO_P
    )


class EngineExecutiveService:
    def __init__(
        self,
        snapshot: ExecutiveSnapshot,
        partners: EnginePartnerService,
        aml: AmlSnapshot,
    ) -> None:
        self._snap = snapshot
        self.provenance_resolver = ProvenanceResolver(create_default_registry())
        self._briefing = BriefingBuilder(snapshot, partners, aml, self.provenance_resolver)
        self._what_if = WhatIfEngine(snapshot, partners)
        self.as_of: datetime = datetime.combine(
            snapshot.world.config.as_of, datetime.min.time(), tzinfo=UTC
        ).replace(hour=8)

    @property
    def snapshot(self) -> ExecutiveSnapshot:
        return self._snap

    def get_morning_briefing(self, as_of: datetime | None = None) -> MorningBriefingDossier:
        when = as_of or self.as_of
        b = self._briefing
        return MorningBriefingDossier(
            briefing_id=f"brf_{when.strftime('%Y%m%d_%H%M')}",
            generated_at=when,
            horizons=[b.competitive(when), b.partner(when), b.client(when), b.financial(when)],
            risks=b.risks(when),
            opportunities=b.opportunities(),
            is_cached_fallback=False,
        )

    def get_causal_dag(self) -> CausalDAGGraph:
        latest = self._snap.latest
        nodes = [
            CausalNode(
                node_id=node_id,
                label=label,
                domain=domain,
                current_value=latest[node_id],
                provenance=self.provenance_resolver.resolve(node_id, as_of=self.as_of),
            )
            for node_id, label, domain in _NODES
        ]
        edges = [
            CausalEdge(
                source_node_id=e.candidate.source,
                target_node_id=e.candidate.target,
                weight=round(e.weight, 6),
                refuter=CausalEdgeRefuterStatus(
                    is_causal_verified=_verified(e),
                    confidence=e.confidence,
                    placebo_effect=e.report.placebo_effect,
                    placebo_p_value=e.report.placebo_p_value,
                    status_label=VERIFIED if _verified(e) else UNVERIFIED,
                ),
            )
            for e in self._snap.fit.edges
        ]
        return CausalDAGGraph(
            dag_version=self._snap.fit.manifest.model_version,
            as_of=self.as_of,
            nodes=nodes,
            edges=edges,
        )

    def get_forecast(self, metric_id: str) -> ForecastView:
        if metric_id != REVENUE:
            raise KeyError(f"no projection exists for {metric_id}")
        f, bt = self._snap.forecast, self._snap.forecast.backtest
        fin = self._briefing.financial(self.as_of)
        return ForecastView(
            metric_id=metric_id,
            point_estimate=round(f.point, 2),
            delta_period_pct=fin.delta_period_pct,
            headline=fin.headline,
            horizon_days=f.horizon,
            interval_low=round(f.low, 2),
            interval_high=round(f.high, 2),
            interval_nominal=bt.nominal,
            interval_coverage=round(bt.coverage_out_of_sample, 3),
            skill_vs_persistence=round(bt.mase, 3),
            backtest_origins=bt.origins,
            assumption="competitor payout rate decays toward its mean at its fitted rate",
        )

    def stage_requests(self) -> dict[str, dict[str, Any]]:
        return self._briefing.stage_requests()

    def shocks(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "competitor_payout_increase",
                "label": "Competitor raises its payout",
                "driver": "Competitor payout rate, % change",
                "level": self._snap.latest[PAYOUT],
            }
        ]

    def current_net_revenue(self) -> float:
        return round(self._snap.latest[REVENUE], 2)

    def shock_path(self, shock_param: str) -> tuple[tuple[str, str], ...]:
        return self._what_if.shock_path(shock_param)

    def simulate_what_if_shock(self, shock_param: str, magnitude_pct: float) -> dict[str, Any]:
        out = self._what_if.simulate(shock_param, magnitude_pct)
        out["causal_label"], out["causal_reason"] = self._causal_label(
            shock_param, bool(out["extrapolates_beyond_history"])
        )
        return out

    def _causal_label(self, shock: str, extrapolates: bool) -> tuple[str, str]:
        """RL-3 for a whole path: causal only if every edge on it is verified and the shock is inside the history."""
        if extrapolates:
            return (
                "CORRELATION_ONLY",
                "the shocked level lies outside anything seen in the history; the fitted effects are not tested there",
            )
        edges = {(e.candidate.source, e.candidate.target): e for e in self._snap.fit.edges}
        for pair in self.shock_path(shock):
            edge = edges.get(pair)
            if edge is None or not _verified(edge):
                return "CORRELATION_ONLY", f"{pair[0]} to {pair[1]} did not pass the causal gate"
        return "VERIFIED_CAUSAL", "every link on the shock path passed the placebo refuter"

    def triage_items(self, now_iso: str) -> list[dict[str, Any]]:
        """The executive triage rail: one item per briefing horizon and top risk, ranked by computed severity."""
        b = self.get_morning_briefing()
        weight = {"HIGH": 0.9, "MEDIUM": 0.6}
        items = [
            {
                "id": f"item_{r.risk_id}",
                "title": r.title,
                "subtitle": f"Exposure ${r.exposure_usd:,.0f}",
                "entity_id": r.risk_id.removeprefix("rsk_partner_").removeprefix("rsk_"),
                "priority_score": weight.get(r.severity, 0.3),
                "severity": r.severity,
                "status": "OPEN",
                "timestamp": now_iso,
            }
            for r in b.risks
        ]
        items += [
            {
                "id": f"item_hz_{h.horizon_name.lower()}",
                "title": f"{h.horizon_name} horizon",
                "subtitle": h.headline,
                "entity_id": h.primary_metric_id,
                "priority_score": min(abs(h.delta_period_pct) / 100.0, 0.5),
                "severity": "LOW",
                "status": "OPEN",
                "timestamp": now_iso,
            }
            for h in b.horizons
        ]
        return sorted(items, key=lambda i: i["priority_score"], reverse=True)

    def summary(self) -> str:
        b = self.get_morning_briefing()
        return " ".join(
            h.headline for h in b.horizons if h.horizon_name in ("Financial", "Partner")
        )
