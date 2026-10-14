"""The AML investigator's screen from the engine plane: ranked cases, one computed dossier, one graph (spec 031 FR-011).

The workstation route and the per-case route both build from here, so what the rail lists and what a selection
opens come from the same objects the assistant's tools read.
"""

from __future__ import annotations

from typing import Any

from eios.cockpit import aml_case_extras as extras
from eios.cockpit.aml import EntityInvestigationDossier
from eios.cockpit.aml_metric import ENGINE_NAME as _ENGINE
from eios.cockpit.aml_metric import metric as _metric
from eios.dataplane.aml_service import CORRELATION_ONLY, EngineAMLService

QUEUE_LIMIT = 50
_SEVERITY = {"CRITICAL": "CRITICAL", "HIGH": "HIGH"}


def triage_items(engine: EngineAMLService, now_iso: str) -> list[dict[str, Any]]:
    """The ranked queue the rail lists: the fifty cases a human reviews, strongest first."""
    return [
        {
            "id": row["alert_id"],
            "title": _title(row),
            "subtitle": row["discrepancy_summary"],
            "entity_id": row["entity_id"],
            "entity_type": "ACCOUNT",
            "priority_score": round(row["risk_score"] / 100.0, 2),
            "severity": _SEVERITY.get(row["tier"], "MEDIUM"),
            "status": "OPEN" if row["status"] == "UNREVIEWED" else "INVESTIGATING",
            "timestamp": now_iso,
            "tags": [row["typology"].replace("_", " ").title()],
        }
        for row in engine.get_triage_cases(min_score=0, limit=QUEUE_LIMIT)
    ]


def _title(row: dict[str, Any]) -> str:
    if row["syndicate_size"] > 1:
        return f"Mule ring {row['entity_id']} (+{row['syndicate_size'] - 1})"
    return f"AML Alert {row['entity_id']}"


def default_entity(engine: EngineAMLService) -> str:
    """The lead account of the strongest case."""
    return str(engine.get_triage_cases(min_score=0, limit=1)[0]["entity_id"])


def active_dossier(engine: EngineAMLService, entity_id: str) -> dict[str, Any]:
    dossier = engine.get_entity_dossier(entity_id)
    view = engine.get_case_view(entity_id)
    as_of = engine.as_of.isoformat()
    sections = [
        _summary(view, as_of),
        _kyc(dossier, as_of),
        _velocity(dossier, view, as_of),
        *_ring(view, as_of),
        *_trading(view, as_of),
        *_withdrawal(engine, entity_id, as_of),
        _causal(view),
        {
            "section_id": "sec_sar_draft",
            "title": "Near-Final SAR Draft Narrative",
            "narrative_text": engine.compose_sar_draft(entity_id=entity_id).narrative_summary,
            "citations": ["realized_deposit_volume_30d_usd", "discrepancy_multiplier"],
            "metrics": [],
        },
    ]
    return {
        "dossier_id": f"dos_{entity_id}",
        "entity_id": entity_id,
        "headline": f"AML Investigation Dossier - Entity {entity_id}",
        "executive_summary": view["headline"],
        "sections": sections,
        "as_of_timestamp": as_of,
        "is_cached_snapshot": False,
        "sar_draft": extras.sar_panel(engine, entity_id),
        "trade_offs": extras.trade_offs(engine, entity_id),
    }


def case_payload(engine: EngineAMLService, entity_id: str) -> dict[str, Any]:
    """Everything the AML screen shows for one account: dossier, network, evidence strip, SAR panel, stage requests."""
    return {
        "entity_id": entity_id,
        "active_dossier": active_dossier(engine, entity_id),
        "kinetic_canvas": kinetic_canvas(engine, entity_id),
        "evidence_strip": extras.evidence_strip(engine, entity_id),
        "sar_draft": extras.sar_panel(engine, entity_id),
        "case_actions": extras.case_actions(engine, entity_id),
        "data_origin": "engine",
    }


def _summary(view: dict[str, Any], as_of: str) -> dict[str, Any]:
    case = view["case"]
    reasons = view["reasons"]
    text = view["headline"] + ("." if not view["headline"].endswith(".") else "")
    if reasons:
        text += " Why it was raised: " + "; ".join(reasons[:3]) + "."
    metrics = (
        []
        if case is None
        else [
            _metric(
                "composite_risk_score",
                f"{case['risk_score']}/100",
                float(case["risk_score"]),
                as_of,
            )
        ]
    )
    return {
        "section_id": "sec_case",
        "title": "Why this case",
        "narrative_text": text,
        "citations": ["composite_risk_score"],
        "metrics": metrics,
    }


def _kyc(d: EntityInvestigationDossier, as_of: str) -> dict[str, Any]:
    k = d.kyc
    return {
        "section_id": "sec_kyc",
        "title": "KYC & Income Declarations",
        "narrative_text": f"Registered in {k.country_of_residence} as {k.employment_status}. Declared income ${k.declared_monthly_income_usd:,.0f}/mo.",
        "citations": ["declared_monthly_income_usd"],
        "metrics": [
            _metric(
                "declared_monthly_income_usd",
                f"${k.declared_monthly_income_usd:,.0f}/mo",
                k.declared_monthly_income_usd,
                as_of,
                engine_name="KYCOntologyService",
            )
        ],
    }


def _velocity(d: EntityInvestigationDossier, view: dict[str, Any], as_of: str) -> dict[str, Any]:
    x, peers = d.discrepancy, view["peer_group_comparison"]
    return {
        "section_id": "sec_velocity",
        "title": "Transaction Velocity & Discrepancy",
        "narrative_text": (
            f"Observed 30-day deposits ${x.realized_deposit_volume_30d_usd:,.0f} vs declared income "
            f"${d.kyc.declared_monthly_income_usd:,.0f}: {x.discrepancy_multiplier:.1f}x. "
            f"Peer cohort {peers['peer_cohort']} median ${peers['median_turnover_usd']:,.0f}, "
            f"{peers['standard_deviations_above_median']:.1f} robust deviations above."
        ),
        "citations": ["realized_deposit_volume_30d_usd", "discrepancy_multiplier"],
        "metrics": [
            {
                **_metric(
                    "realized_deposit_volume_30d_usd",
                    f"${x.realized_deposit_volume_30d_usd:,.0f}",
                    x.realized_deposit_volume_30d_usd,
                    x.provenance.as_of_timestamp.isoformat(),
                    engine_name=_ENGINE,
                ),
                "semantic_definition_version": x.provenance.definition_version,
                "steward_role": x.provenance.owner_role,
            },
            _metric(
                "discrepancy_multiplier",
                f"{x.discrepancy_multiplier:.1f}x",
                x.discrepancy_multiplier,
                as_of,
            ),
        ],
    }


def _ring(view: dict[str, Any], as_of: str) -> list[dict[str, Any]]:
    ring = view["ring"]
    if ring is None:
        return []
    return [
        {
            "section_id": "sec_network",
            "title": "Network & Ring Evidence",
            "narrative_text": f"{ring['size']} accounts share a device fingerprint and deposit in matched bursts. Public gateways above the hub limit are collapsed, not merged.",
            "citations": ["syndicate_ring_size"],
            "metrics": [
                _metric(
                    "syndicate_ring_size",
                    f"{ring['size']} accounts",
                    float(ring["size"]),
                    as_of,
                    engine_name="MuleRingDetector",
                )
            ],
        }
    ]


def _trading(view: dict[str, Any], as_of: str) -> list[dict[str, Any]]:
    ev = view["evidence"]
    if ev["trade_count"] <= 0:
        return []
    return [
        {
            "section_id": "sec_trading",
            "title": "Trading Behaviour",
            "narrative_text": f"{int(ev['trade_count'])} trades with a net P&L of ${ev['net_trading_pnl_usd']:+,.2f} against ${ev['realized_deposit_volume_30d_usd']:,.0f} deposited; {ev['withdrawn_share']:.0%} withdrawn.",
            "citations": ["net_trading_pnl_usd"],
            "metrics": [
                _metric(
                    "net_trading_pnl_usd",
                    f"${ev['net_trading_pnl_usd']:+,.2f}",
                    ev["net_trading_pnl_usd"],
                    as_of,
                    engine_name="RoundTripDetector",
                )
            ],
        }
    ]


def _withdrawal(engine: EngineAMLService, entity_id: str, as_of: str) -> list[dict[str, Any]]:
    pending = engine.get_pending_withdrawal(entity_id)
    if pending is None:
        return []
    return [
        {
            "section_id": "sec_withdrawal",
            "title": "Pending Withdrawal",
            "narrative_text": f"Withdrawal {pending.withdrawal_id} of ${pending.amount_usd:,.0f} is pending, {pending.hours_since_deposit:.1f} hours after the last deposit.",
            "citations": ["pending_withdrawal_usd"],
            "metrics": [
                _metric(
                    "pending_withdrawal_usd",
                    f"${pending.amount_usd:,.0f}",
                    pending.amount_usd,
                    as_of,
                    engine_name="WithdrawalSentinel",
                )
            ],
        }
    ]


def _causal(view: dict[str, Any]) -> dict[str, Any]:
    ref = view["refutation"]
    if ref is None:
        text = f"{CORRELATION_ONLY}: no ring link, so no causal claim is made for this account."
    else:
        text = f"{view['causal_label']}: placebo p-value {ref['placebo_p_value']:.2f}, verdict {ref['gate_verdict']}."
    return {
        "section_id": "sec_causal",
        "title": "Evidence Strength",
        "narrative_text": text,
        "citations": [],
        "metrics": [],
    }


def kinetic_canvas(engine: EngineAMLService, entity_id: str) -> dict[str, Any]:
    graph = engine.get_kinetic_network_graph(entity_id)
    return {
        "canvas_type": "TOPOLOGICAL_GRAPH",
        "payload": {
            "nodes": [n.model_dump() for n in graph.nodes],
            "edges": [e.model_dump() for e in graph.edges],
            "cgnat_suppressed": True,
            "hub_count_suppressed": sum(1 for n in graph.nodes if n.is_hub_suppressed),
        },
    }
