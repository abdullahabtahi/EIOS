"""The partner read model over the engines: the methods the screen and the assistant already call (spec 032 FR-007).

It satisfies `PartnerReadModel`, so the port and the routes cannot tell it from the fixture service, except that
every partner on the radar has computed signals, deals, integrity evidence and messages. Referral counts and AML
exposure come from the AML world, whose clients name the partner that referred them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from eios.cockpit.partner import (
    ChurnRadarScatter,
    PartnerChurnItem,
    PartnerQuadrant,
    RetentionPlaybookDeal,
)
from eios.cockpit.partner_readmodel import PartnerMessage
from eios.cockpit.provenance import ProvenanceResolver
from eios.dataplane import partner_integrity as integrity
from eios.dataplane.aml_engine import AmlSnapshot
from eios.dataplane.partner_engine import HIGH_RISK, PartnerSnapshot, expected_days_to_churn
from eios.dataplane.partner_evidence import PartnerEvidence, build_evidence
from eios.dataplane.partner_playbooks import Counterfactual, deals, playbooks_for
from eios.foundry.scenarios.partner_config import PARTNER_ALIASES

HIGH_VALUE_QUANTILE = 0.75  # [ASSUMPTION] the top quarter of 30-day volume is "high value"
_ENGINE = "ChurnRadarPipeline"


class UnknownPartnerError(LookupError):
    """The partner world holds no such partner."""


def _drift(now: float, value: float, past: dict[int, tuple[float, float]]) -> dict[str, Any] | None:
    if 30 not in past or 14 not in past:
        return None
    (h30, v30), (h14, v14) = past[30], past[14]
    return {
        "tMinus30d": {"pChurn": round(h30, 4), "valueAtRiskUsd": round(h30 * v30, 2)},
        "tMinus14d": {"pChurn": round(h14, 4), "valueAtRiskUsd": round(h14 * v14, 2)},
        "driftVelocityPct": round((now - h30) / max(h30, 0.01) * 100.0, 1),
    }


class EnginePartnerService:
    def __init__(
        self,
        snapshot: PartnerSnapshot,
        aml: AmlSnapshot | None = None,
        provenance: ProvenanceResolver | None = None,
    ) -> None:
        self._snap = snapshot
        self._aml = aml
        self.provenance_resolver = provenance or ProvenanceResolver()
        self.as_of: datetime = snapshot.world.config.as_of
        self._roster = snapshot.world.roster.set_index("partner_id")
        self._evidence = build_evidence(snapshot.world, snapshot.scored, snapshot.contributions)
        self._cf = Counterfactual()
        self._value_line = float(
            snapshot.scored["realized_volume_30d_usd"].quantile(HIGH_VALUE_QUANTILE)
        )
        self._radar = self._build_radar()

    @property
    def snapshot(self) -> PartnerSnapshot:
        return self._snap

    # --- lookup -------------------------------------------------------------------------------------------

    def resolve(self, ref: str) -> str:
        pid = PARTNER_ALIASES.get(ref.strip().upper(), ref.strip().upper())
        if pid not in self._snap.scored.index:
            raise UnknownPartnerError(ref)
        return pid

    def has_detail(self, partner_id: str) -> bool:
        return partner_id in self._snap.scored.index

    def evidence(self, partner_id: str) -> PartnerEvidence:
        return self._evidence[self.resolve(partner_id)]

    def row(self, partner_id: str) -> pd.Series:
        return self._snap.scored.loc[self.resolve(partner_id)]

    def counterfactual(self) -> Counterfactual:
        return self._cf

    # --- radar --------------------------------------------------------------------------------------------

    def _quadrant(self, hazard: float, value: float) -> PartnerQuadrant:
        high_value = value >= self._value_line
        if hazard >= HIGH_RISK:
            return (
                PartnerQuadrant.HIGH_VALUE_HIGH_RISK
                if high_value
                else PartnerQuadrant.LOW_VALUE_HIGH_RISK
            )
        return PartnerQuadrant.HIGH_VALUE_STABLE if high_value else PartnerQuadrant.LOW_VALUE_STABLE

    def _item(self, pid: str, row: pd.Series) -> PartnerChurnItem:
        ev = self._evidence[pid]
        meta = self._roster.loc[pid]
        hazard = round(float(row["hazard_probability_30d"]), 4)
        value = round(float(row["realized_volume_30d_usd"]), 2)
        past = {
            back: (float(h.loc[pid, "hazard_probability_30d"]), float(h.loc[pid, "value_at_risk"]))
            for back, h in self._snap.history.items()
            if pid in h.index
        }
        best = max(
            (self._cf.project(row, pb) for pb in playbooks_for(ev)),
            key=lambda p: p.net_margin_usd,
            default=None,
        )
        exposure = integrity.pair_exposure(self._snap, self._children(pid) | {pid})
        return PartnerChurnItem(
            partner_id=pid,
            name=str(meta["name"]),
            realized_volume_30d_usd=value,
            churn_hazard_probability=hazard,
            quadrant=self._quadrant(hazard, value),
            days_to_intervention_deadline=expected_days_to_churn(hazard),
            primary_root_cause=ev.root_cause,
            login_decay_pct=round(-float(row["login_velocity_decay_3w"]) * 100.0, 1),
            ftd_decay_pct=round(float(row["ftd_volume_delta_pct"]) * 100.0, 1),
            provenance=self.provenance_resolver.resolve(
                "churn_hazard_probability", as_of=self.as_of
            ),
            tier=str(meta["tier"]),
            region=str(meta["market"]),
            cohort=str(meta["cohort"]),
            historical_drift=_drift(hazard, value, past),
            empirical_win_rate=None,  # no playbook outcome history exists yet
            primary_driver=ev.driver,
            change_point_flag=bool(row.get("seasonal_dip_flag", False)),
            support_ticket_count=ev.negative_messages,
            cashier_latency_sla_hours=ev.payout_latency_hours,
            competitor_poaching=ev.rival,
            mirror_trade_correlation=exposure.max_confidence,
            extracted_commission_usd=exposure.commission_usd,
            projected_lift_pct=best.uplift_pct if best else None,
            net_margin_recovery_usd=best.net_margin_usd if best else None,
        )

    def _build_radar(self) -> ChurnRadarScatter:
        ranked = self._snap.scored.sort_values("priority_score", ascending=False)
        return ChurnRadarScatter(
            as_of=self.as_of, partners=[self._item(str(pid), row) for pid, row in ranked.iterrows()]
        )

    def get_churn_radar_scatter(self) -> ChurnRadarScatter:
        return self._radar

    # --- deals, tree, messages ----------------------------------------------------------------------------

    def get_retention_playbooks(self, partner_id: str = "") -> list[RetentionPlaybookDeal]:
        pid = self.resolve(partner_id)
        return deals(pid, self._snap.scored.loc[pid], self._evidence[pid], self._cf)

    def _children(self, pid: str) -> set[str]:
        roster = self._snap.world.roster
        return set(roster.loc[roster["parent_id"] == pid, "partner_id"])

    def get_partner_referral_tree(self, partner_id: str = "") -> dict[str, Any]:
        pid = self.resolve(partner_id)
        return integrity.referral_tree(self._snap, self._aml, pid, self._children(pid))

    def get_messages(self, partner_id: str) -> list[PartnerMessage]:
        pid = self.resolve(partner_id)
        rows = self._snap.world.messages
        return [
            PartnerMessage(
                message_id=str(m["message_id"]),
                channel=str(m["channel"]),
                sentiment=str(m["sentiment"]),
                topic=str(m["topic"]),
                received_at=pd.Timestamp(m["timestamp"]).to_pydatetime().replace(tzinfo=UTC),
                text=str(m["text"]),
            )
            for _, m in rows[rows["partner_id"] == pid].iterrows()
        ]

    def partner_ids(self) -> list[str]:
        return [p.partner_id for p in self._radar.partners]

    def stats(self) -> dict[str, Any]:
        q = self._snap.quality
        return {k: getattr(q, k) for k in q.__dataclass_fields__}
