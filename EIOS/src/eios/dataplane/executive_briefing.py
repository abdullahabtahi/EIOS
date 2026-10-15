"""The four-horizon morning briefing, computed (spec 034).

Each horizon reads the engine that owns it: the firm series (competitive and financial), the partner engine, and the
AML engine. Every number in a headline is formatted from a value computed here; nothing is typed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from eios.cockpit.executive import (
    HorizonSummary,
    StrategicOpportunity,
    StrategicRisk,
)
from eios.cockpit.provenance import ProvenanceResolver
from eios.dataplane.aml_engine import AmlSnapshot
from eios.dataplane.executive_engine import ExecutiveSnapshot
from eios.dataplane.partner_engine import HIGH_RISK
from eios.dataplane.partner_playbooks import FAST_PATH_BUDGET_USD, playbooks_for
from eios.dataplane.partner_service import EnginePartnerService
from eios.foundry.scenarios.executive_world import PAYOUT, REVENUE

LOOKBACK_DAYS = 28
HIGH_SEVERITY_HAZARD = 0.70  # [ASSUMPTION] a partner this likely to churn is a HIGH risk
HIGH_SEVERITY_AML = 0.80


def _pct(now: float, before: float) -> float:
    return round((now / before - 1.0) * 100.0, 2) if before else 0.0


class BriefingBuilder:
    def __init__(
        self,
        snapshot: ExecutiveSnapshot,
        partners: EnginePartnerService,
        aml: AmlSnapshot,
        resolver: ProvenanceResolver,
    ) -> None:
        self._exec, self._partners, self._aml, self._resolver = snapshot, partners, aml, resolver

    # --- horizons ------------------------------------------------------------------------------------------

    def competitive(self, as_of: datetime) -> HorizonSummary:
        days = self._exec.world.days
        now, before = float(days[PAYOUT].iloc[-1]), float(days[PAYOUT].iloc[-1 - LOOKBACK_DAYS])
        delta = _pct(now, before)
        median = float(days[PAYOUT].median())
        return HorizonSummary(
            horizon_name="Competitive",
            headline=(
                f"Competitor payout rate is {now:.3f}, {delta:+.1f}% over {LOOKBACK_DAYS} days "
                f"(two-year median {median:.3f})."
            ),
            primary_metric_id=PAYOUT,
            observed_value=round(now, 4),
            delta_period_pct=delta,
            provenance=self._resolver.resolve(PAYOUT, as_of=as_of),
        )

    def partner(self, as_of: datetime) -> HorizonSummary:
        snap = self._partners.snapshot
        scored = snap.scored
        high = scored[scored["hazard_probability_30d"] >= HIGH_RISK]
        volume = float(high["realized_volume_30d_usd"].sum())
        then = snap.history[max(snap.history)]
        past_high = then[then["hazard_probability_30d"] >= HIGH_RISK]
        cohort = next(iter(snap.cohorts), None)
        tail = (
            f" A synchronised {cohort.region_id} cohort of {cohort.partner_count} partners is flagged."
            if cohort
            else ""
        )
        return HorizonSummary(
            horizon_name="Partner",
            headline=(
                f"{len(high)} partners are above a {HIGH_RISK:.0%} 30-day churn hazard and carry "
                f"${volume:,.0f} of 30-day volume.{tail}"
            ),
            primary_metric_id="realized_volume_30d_usd",
            observed_value=round(volume, 2),
            delta_period_pct=_pct(volume, float(past_high["value_at_risk"].sum())),
            provenance=self._resolver.resolve("realized_volume_30d_usd", as_of=as_of),
        )

    def _ring_members(self) -> tuple[tuple[str, ...], str, int]:
        top = [c for c in self._aml.cases if c.in_top_k]
        members = tuple(dict.fromkeys(m for c in top for m in c.members))
        ring = max(top, key=lambda c: c.ring_size, default=None)
        return members, (ring.ring_id or "" if ring else ""), (ring.ring_size if ring else 0)

    def _deposit_pace(self, members: tuple[str, ...]) -> tuple[float, float]:
        tx = self._aml.world.transactions
        dep = tx[(tx["transaction_type"] == "DEPOSIT") & (tx["client_id"].isin(members))]
        if dep.empty:
            return 0.0, 0.0
        mid = dep["timestamp"].min() + (dep["timestamp"].max() - dep["timestamp"].min()) / 2
        late = float(dep.loc[dep["timestamp"] > mid, "amount"].sum())
        return late, float(dep.loc[dep["timestamp"] <= mid, "amount"].sum())

    def client(self, as_of: datetime) -> HorizonSummary:
        members, _ring, ring_size = self._ring_members()
        facts = self._aml.facts
        volume = float(facts.loc[facts.index.isin(members), "dep_volume"].sum())
        late, early = self._deposit_pace(members)
        top = sum(1 for c in self._aml.cases if c.in_top_k)
        return HorizonSummary(
            horizon_name="Client",
            headline=(
                f"{top} priority AML cases cover {len(members)} accounts holding ${volume:,.0f} of "
                f"30-day deposits; the largest ring links {ring_size} accounts."
            ),
            primary_metric_id="realized_deposit_volume_30d_usd",
            observed_value=round(volume, 2),
            delta_period_pct=_pct(late, early),  # the window's second half against its first
            provenance=self._resolver.resolve("realized_deposit_volume_30d_usd", as_of=as_of),
        )

    def financial(self, as_of: datetime) -> HorizonSummary:
        f = self._exec.forecast
        now = self._exec.latest[REVENUE]
        delta = _pct(f.point, now)
        return HorizonSummary(
            horizon_name="Financial",
            headline=(
                f"Net revenue is projected at ${f.point:,.0f} in {f.horizon} days "
                f"({f.backtest.nominal:.0%} interval ${f.low:,.0f} to ${f.high:,.0f}), "
                f"{delta:+.1f}% against today."
            ),
            primary_metric_id=REVENUE,
            observed_value=round(f.point, 2),
            delta_period_pct=delta,
            provenance=self._resolver.resolve(REVENUE, as_of=as_of),
        )

    # --- risks and opportunities ---------------------------------------------------------------------------

    def _top_partners(self, n: int) -> pd.DataFrame:
        scored = self._partners.snapshot.scored
        exposure = scored["hazard_probability_30d"] * scored["realized_volume_30d_usd"]
        return scored.assign(exposure=exposure).sort_values("exposure", ascending=False).head(n)

    def risks(self, as_of: datetime) -> list[StrategicRisk]:
        out: list[StrategicRisk] = []
        roster = self._partners.snapshot.world.roster.set_index("partner_id")
        for pid, row in self._top_partners(2).iterrows():
            hazard = float(row["hazard_probability_30d"])
            out.append(
                StrategicRisk(
                    risk_id=f"rsk_partner_{pid}",
                    title=f"{roster.loc[pid, 'name']} ({pid}) is likely to disengage",
                    severity="HIGH" if hazard >= HIGH_SEVERITY_HAZARD else "MEDIUM",
                    exposure_usd=round(float(row["exposure"]), 2),
                    provenance=self._resolver.resolve("realized_volume_30d_usd", as_of=as_of),
                )
            )
        members, ring_id, ring_size = self._ring_members()
        if ring_id:
            facts = self._aml.facts
            top = max((c for c in self._aml.cases if c.in_top_k), key=lambda c: c.ring_size)
            out.append(
                StrategicRisk(
                    risk_id=f"rsk_ring_{ring_id}",
                    title=f"Linked-account ring of {ring_size} accounts",
                    severity="HIGH" if top.risk >= HIGH_SEVERITY_AML else "MEDIUM",
                    exposure_usd=round(
                        float(facts.loc[facts.index.isin(top.members), "dep_volume"].sum()), 2
                    ),
                    provenance=self._resolver.resolve(
                        "realized_deposit_volume_30d_usd", as_of=as_of
                    ),
                )
            )
        return out

    def _opportunity_rows(self) -> list[tuple[StrategicOpportunity, dict[str, Any]]]:
        cf = self._partners.counterfactual()
        out: list[tuple[StrategicOpportunity, dict[str, Any]]] = []
        roster = self._partners.snapshot.world.roster.set_index("partner_id")
        for pid, row in self._top_partners(3).iterrows():
            options = [
                (pb, cf.project(row, pb)) for pb in playbooks_for(self._partners.evidence(str(pid)))
            ]
            best = max(options, key=lambda o: o[1].net_margin_usd, default=None)
            if best is None or best[1].net_margin_usd <= 0:
                continue
            pb, proj = best
            opportunity = StrategicOpportunity(
                opportunity_id=f"opp_{pb.playbook_id}_{pid}",
                title=f"{pb.title} for {roster.loc[pid, 'name']}",
                projected_upside_usd=proj.net_margin_usd,
                recommended_action_type=pb.action_type,
            )
            request = {
                "action_type": pb.action_type,
                "target_entity_id": str(pid),
                "severity": "MEDIUM",
                "requires_four_eyes": proj.cost_usd > FAST_PATH_BUDGET_USD,
                "metadata": {
                    "partner_ids": [str(pid)],
                    "playbook_id": pb.playbook_id,
                    "budget": proj.cost_usd,
                },
            }
            out.append((opportunity, request))
        return out

    def opportunities(self) -> list[StrategicOpportunity]:
        return [o for o, _ in self._opportunity_rows()]

    def stage_requests(self) -> dict[str, dict[str, Any]]:
        """The request that stages each opportunity through the intent hub, by opportunity id."""
        return {o.opportunity_id: r for o, r in self._opportunity_rows()}
