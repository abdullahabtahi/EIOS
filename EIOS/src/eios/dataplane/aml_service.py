"""The AML read model over the engine: the same methods the screen and the assistant already call (spec 031 FR-007).

It satisfies `AmlReadModel`, so the tool port and the workstation routes cannot tell it from the fixture service,
except that every account the world holds has a computed dossier, graph, timeline and SAR draft.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime
from typing import Any

import pandas as pd

from eios.aml.case_views import PendingWithdrawal, TimelineEvent
from eios.cockpit.aml import (
    EntityInvestigationDossier,
    KineticNetworkGraph,
    KYCDeclaration,
    SARDraftDocument,
    TransactionVelocityDiscrepancy,
)
from eios.cockpit.provenance import ProvenanceResolver
from eios.dataplane import aml_narrative as narrative
from eios.dataplane.aml_cases import AmlCase
from eios.dataplane.aml_engine import AmlSnapshot
from eios.dataplane.aml_graph import build_graph
from eios.dataplane.aml_text import headline

CAUSAL_VERIFIED = "Verified causal"
CORRELATION_ONLY = "Correlation Only"
_MAD_SCALE = 1.4826


class UnknownAccountError(LookupError):
    """The world holds no such account."""


def normalize_ref(ref: str) -> str:
    """`case_aml_CR84920`, `ALT-CR84920`, `CR84920` and `84920` all name the same account."""
    text = ref.strip().upper().removeprefix("CASE_AML_").removeprefix("ALT-")
    return text if text.startswith("CR") else f"CR{text}"


def _cluster_key(seed: str) -> str:
    return "tok_id_cluster_" + hashlib.sha256(seed.encode()).hexdigest()[:16]


class EngineAMLService:
    def __init__(self, snapshot: AmlSnapshot, provenance: ProvenanceResolver | None = None) -> None:
        self._snap = snapshot
        self._provenance = provenance or ProvenanceResolver()
        self.as_of: datetime = pd.Timestamp(snapshot.world.config.as_of).to_pydatetime()

    @property
    def snapshot(self) -> AmlSnapshot:
        return self._snap

    # --- lookup -------------------------------------------------------------------------------------------

    def _row(self, entity_id: str) -> pd.Series:
        if entity_id not in self._snap.facts.index:
            raise UnknownAccountError(entity_id)
        return self._snap.facts.loc[entity_id]

    def account_ids(self) -> list[str]:
        return [str(i) for i in self._snap.facts.index]

    def supports_detail(self, entity_id: str) -> bool:
        return entity_id in self._snap.facts.index

    def get_alert_score(self, entity_id: str) -> int | None:
        case = self._snap.case_for(entity_id)
        return None if case is None else round(case.risk * 100)

    # --- triage -------------------------------------------------------------------------------------------

    def get_triage_cases(self, min_score: int = 0, limit: int = 50) -> list[dict[str, Any]]:
        """Ranked cases above `min_score`, with everything the rail shows."""
        out: list[dict[str, Any]] = []
        for case in self._snap.cases:
            if round(case.risk * 100) < min_score:
                continue
            out.append(self._case_row(case))
            if len(out) >= limit:
                break
        return out

    def _case_row(self, case: AmlCase) -> dict[str, Any]:
        row = self._row(case.client_id)
        age = (
            self.as_of - pd.Timestamp(row["last_activity"]).to_pydatetime()
        ).total_seconds() / 3600.0
        return {
            "alert_id": case.alert_id,
            "entity_id": case.client_id,
            "risk_score": round(case.risk * 100),
            "discrepancy_summary": headline(case, row),
            "syndicate_size": case.ring_size,
            "age_hours": round(max(age, 0.0), 1),
            "status": case.status,
            "rank": case.rank,
            "tier": case.tier.value,
            "typology": case.typology.value,
            "rules": list(case.rules),
            "ring_id": case.ring_id,
            "in_top_k": case.in_top_k,
        }

    def get_triage_queue(self, min_score: int = 50, limit: int = 10) -> list[dict[str, Any]]:
        keys = (
            "alert_id",
            "entity_id",
            "risk_score",
            "discrepancy_summary",
            "syndicate_size",
            "age_hours",
            "status",
        )
        return [{k: r[k] for k in keys} for r in self.get_triage_cases(min_score, limit)]

    # --- dossier, graph, SAR ------------------------------------------------------------------------------

    def get_entity_dossier(self, entity_id: str) -> EntityInvestigationDossier:
        row = self._row(entity_id)
        case = self._snap.case_for(entity_id)
        income = max(float(row["declared_monthly_income_usd"]), 1.0)
        volume = float(row["dep_volume"])
        ring_size = case.ring_size if case else 1
        return EntityInvestigationDossier(
            case_id=f"case_aml_{entity_id}",
            entity_id=entity_id,
            identity_cluster_key=_cluster_key(case.ring_id if case and case.ring_id else entity_id),
            composite_risk_score=round(case.risk * 100) if case else 0,
            kyc=KYCDeclaration(
                declared_monthly_income_usd=float(row["declared_monthly_income_usd"]),
                employment_status=str(row["employment_status"]),
                country_of_residence=str(row["country"]),
                kyc_approval_timestamp=pd.Timestamp(row["kyc_approved_at"]).to_pydatetime(),
            ),
            discrepancy=TransactionVelocityDiscrepancy(
                realized_deposit_volume_30d_usd=round(volume, 2),
                discrepancy_multiplier=round(volume / income, 1),
                crypto_usdt_deposit_ratio=round(float(row["usdt_volume"]) / volume, 2)
                if volume
                else 0.0,
                provenance=self._provenance.resolve(
                    "realized_deposit_volume_30d_usd", as_of=self.as_of
                ),
            ),
            syndicate_ring_size=ring_size,
            dowhy_refuter_confirmed=self._causal_confirmed(case),
            is_withdrawal_held=False,
        )

    def _causal_confirmed(self, case: AmlCase | None) -> bool:
        return bool(case and case.ring_id and self._snap.ring_refutation.gate_verdict == "PASS")

    def get_kinetic_network_graph(
        self, entity_id: str, hub_threshold: int = 100
    ) -> KineticNetworkGraph:
        self._row(entity_id)
        return build_graph(self._snap, entity_id, hub_threshold)

    def compose_sar_draft(
        self, case_id: str = "", entity_id: str = "", investigator_id: str = ""
    ) -> SARDraftDocument:
        entity = normalize_ref(entity_id or case_id)
        self._row(entity)
        case = self._snap.case_for(entity)
        key = _cluster_key(case.ring_id if case and case.ring_id else entity)
        return SARDraftDocument(
            sar_id=f"sar_{self.as_of:%Y%m%d}_{entity}",
            case_id=case_id or f"case_aml_{entity}",
            subject_entity_id=entity,
            pseudonymized_cluster_key=key,
            narrative_summary=narrative.sar_narrative(self._snap, entity, case, key),
            cited_metric_ids=["realized_deposit_volume_30d_usd", "discrepancy_multiplier"],
            statutory_citations=[],
            created_at=self.as_of,
            investigator_id=investigator_id or "INV-000",
        )

    # --- evidence -----------------------------------------------------------------------------------------

    def get_activity_timeline(self, entity_id: str) -> list[TimelineEvent] | None:
        self._row(entity_id)
        return narrative.timeline(self._snap, entity_id)

    def get_pending_withdrawal(self, entity_id: str) -> PendingWithdrawal | None:
        self._row(entity_id)
        return narrative.pending_withdrawal(self._snap, entity_id)

    def get_case_view(self, entity_id: str) -> dict[str, Any]:
        """What the investigator's screen needs beyond the contract objects: reasons, peers, ring, causal label."""
        row = self._row(entity_id)
        case = self._snap.case_for(entity_id)
        return {
            "entity_id": entity_id,
            "headline": headline(case, row) if case else "No surveillance alert on this account",
            "case": self._case_row(case) if case else None,
            "reasons": list(case.reasons) if case else [],
            "ring": self._ring_view(case),
            "peer_group_comparison": self._peers(row),
            "evidence": self._evidence(row),
            "causal_label": CAUSAL_VERIFIED if self._causal_confirmed(case) else CORRELATION_ONLY,
            "refutation": self._snap.ring_refutation.model_dump()
            if case and case.ring_id
            else None,
        }

    def _ring_view(self, case: AmlCase | None) -> dict[str, Any] | None:
        if case is None or not case.ring_id:
            return None
        return {"ring_id": case.ring_id, "size": case.ring_size, "members": list(case.members)}

    def _peers(self, row: pd.Series) -> dict[str, Any]:
        facts = self._snap.facts
        peers = facts[(facts["cohort_id"] == row["cohort_id"]) & (facts["dep_volume"] > 0)][
            "dep_volume"
        ]
        median = float(peers.median()) if len(peers) else 0.0
        mad = float((peers - median).abs().median()) if len(peers) else 0.0
        z = (float(row["dep_volume"]) - median) / max(_MAD_SCALE * mad, 1.0)
        return {
            "peer_cohort": f"{row['employment_status']} ({row['country']})",
            "median_turnover_usd": round(median, 2),
            "entity_turnover_usd": round(float(row["dep_volume"]), 2),
            "standard_deviations_above_median": round(z, 2),
            "p_value": round(math.erfc(max(z, 0.0) / math.sqrt(2.0)) / 2.0, 6),
        }

    def _evidence(self, row: pd.Series) -> dict[str, float]:
        return {
            "declared_monthly_income_usd": float(row["declared_monthly_income_usd"]),
            "realized_deposit_volume_30d_usd": round(float(row["dep_volume"]), 2),
            "withdrawn_share": round(float(row["dw_ratio"]), 3),
            "trade_count": float(row["trade_count"]),
            "net_trading_pnl_usd": round(float(row["net_pnl"]), 2),
        }

    def stats(self) -> dict[str, Any]:
        q = self._snap.quality
        return {
            "raw_alerts": q.raw_alerts,
            "cases": q.cases,
            "top_k": q.top_k,
            "accounts": len(self._snap.facts),
            "precision_at_k": q.precision_at_k,
            "recall_at_k": q.recall_at_k,
            "ring_recovery": q.ring_recovery,
        }
