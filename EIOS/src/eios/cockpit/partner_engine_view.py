"""The partner workstation payload over the engine plane (spec 032): ranked rail, computed dossier, radar and tree.

Every figure is read from `EnginePartnerService`; a value the platform did not compute is left out. Retention deals
carry stage requests the intent hub understands, so a click stages a signed intent instead of drawing a card.
"""

from __future__ import annotations

from typing import Any

from eios.cockpit.aml_metric import metric
from eios.dataplane.partner_engine import HIGH_RISK
from eios.dataplane.partner_playbooks import FAST_PATH_BUDGET_USD, PROJECTION_BASIS, playbooks_for
from eios.dataplane.partner_service import EnginePartnerService

QUEUE_LIMIT = 50
_STEWARD = "PartnerOperationsSteward"
_ENGINE = "ChurnRadarPipeline"


def _m(metric_id: str, formatted: str, raw: float, as_of: str) -> dict[str, Any]:
    return metric(metric_id, formatted, raw, as_of, engine_name=_ENGINE, steward=_STEWARD)


def _severity(hazard: float) -> str:
    if hazard >= 0.8:
        return "CRITICAL"
    return "HIGH" if hazard >= HIGH_RISK else "MEDIUM"


def triage_items(svc: EnginePartnerService, now_iso: str) -> list[dict[str, Any]]:
    """Partners ranked by expected loss (hazard times 30-day volume), as the pipeline prioritises them."""
    return [
        {
            "id": f"item_{p.partner_id}",
            "title": f"{p.name} ({p.partner_id})",
            "subtitle": p.primary_root_cause,
            "entity_id": p.partner_id,
            "entity_type": "PARTNER",
            "priority_score": round(p.churn_hazard_probability, 2),
            "severity": _severity(p.churn_hazard_probability),
            "status": "OPEN",
            "timestamp": now_iso,
            "tags": [p.region or "", (p.primary_driver or "").replace("_", " ").title()],
        }
        for p in svc.get_churn_radar_scatter().partners[:QUEUE_LIMIT]
    ]


def default_partner(svc: EnginePartnerService) -> str:
    return svc.get_churn_radar_scatter().partners[0].partner_id


def _signals_section(svc: EnginePartnerService, pid: str, as_of: str) -> dict[str, Any]:
    item = next(p for p in svc.get_churn_radar_scatter().partners if p.partner_id == pid)
    ev = svc.evidence(pid)
    text = (
        f"Logins {item.login_decay_pct:+.1f}% and first deposits {item.ftd_decay_pct:+.1f}% over the last two weeks "
        f"against the two before. Median payout time {ev.payout_latency_hours:.1f} h "
        f"(the four weeks before: {ev.baseline_latency_hours:.1f} h); {ev.negative_messages} negative messages on file."
    )
    return {
        "section_id": "sec_signals",
        "title": "Engagement and service signals",
        "narrative_text": text,
        "citations": ["login_decay_pct", "ftd_decay_pct", "payout_latency_hours"],
        "metrics": [
            _m("login_decay_pct", f"{item.login_decay_pct:+.1f}%", item.login_decay_pct, as_of),
            _m("ftd_decay_pct", f"{item.ftd_decay_pct:+.1f}%", item.ftd_decay_pct, as_of),
            _m(
                "payout_latency_hours",
                f"{ev.payout_latency_hours:.1f} h",
                ev.payout_latency_hours,
                as_of,
            ),
        ],
    }


def _risk_section(svc: EnginePartnerService, pid: str, as_of: str) -> dict[str, Any]:
    item = next(p for p in svc.get_churn_radar_scatter().partners if p.partner_id == pid)
    drift = item.historical_drift or {}
    past = drift.get("tMinus30d", {}).get("pChurn")
    trend = f" Thirty days ago it was {past:.0%}." if past is not None else ""
    return {
        "section_id": "sec_risk",
        "title": "Disengagement risk",
        "narrative_text": (
            f"Current disengagement risk {item.churn_hazard_probability:.0%} on ${item.realized_volume_30d_usd:,.0f} of "
            f"30-day referred deposits. Primary driver: {item.primary_root_cause.lower()}.{trend}"
        ),
        "citations": ["churn_hazard_probability", "realized_volume_30d_usd"],
        "metrics": [
            _m(
                "churn_hazard_probability",
                f"{item.churn_hazard_probability:.1%}",
                item.churn_hazard_probability,
                as_of,
            ),
            _m(
                "realized_volume_30d_usd",
                f"${item.realized_volume_30d_usd:,.0f}",
                item.realized_volume_30d_usd,
                as_of,
            ),
        ],
    }


def _integrity_section(tree: dict[str, Any]) -> dict[str, Any]:
    rings = tree["detected_abusive_rings"]
    exposure = tree["aml_exposure"]
    parts = [
        f"{len(rings)} opposite-trading pair{'s' if len(rings) != 1 else ''} across this partner's network"
        if rings
        else "No opposite-trading pairs found in this partner's referred-account trades",
        f"{len(exposure)} prioritised AML case{'s' if len(exposure) != 1 else ''} among its referrals"
        if exposure
        else "no prioritised AML case among its referrals",
    ]
    return {
        "section_id": "sec_integrity",
        "title": "Network integrity",
        "narrative_text": "; ".join(parts) + ". " + tree["statement"],
        "citations": ["opposite_trading_pairs", "aml_cases"],
        "metrics": [],
    }


def trade_offs(svc: EnginePartnerService, pid: str) -> list[dict[str, Any]]:
    row = svc.row(pid)
    cf = svc.counterfactual()
    out: list[dict[str, Any]] = []
    for pb in playbooks_for(svc.evidence(pid)):
        p = cf.project(row, pb)
        out.append(
            {
                "proposedAction": pb.title,
                "projectedReturn": f"hazard {p.hazard_now:.0%} to {p.hazard_after:.0%}; net ${p.net_margin_usd:,.0f} over a quarter",
                "projectedRisk": f"cost ${p.cost_usd:,.0f}; "
                + (
                    "a second approver is required"
                    if p.cost_usd > FAST_PATH_BUDGET_USD
                    else "one approver"
                ),
                "confidenceScore": round(p.uplift_pct / 100.0, 2),
                "downsideSensitivity": PROJECTION_BASIS,
                "evidenceCitations": ["churn_hazard_probability", "realized_volume_30d_usd"],
                "stageRequest": {
                    "action_type": pb.action_type,
                    "target_entity_id": pid,
                    "severity": "MEDIUM",
                    "requires_four_eyes": p.cost_usd > FAST_PATH_BUDGET_USD,
                    "metadata": {
                        "partner_id": pid,
                        "playbook_id": pb.playbook_id,
                        "budget": p.cost_usd,
                    },
                },
            }
        )
    return out


def active_dossier(svc: EnginePartnerService, pid: str) -> dict[str, Any]:
    as_of = svc.as_of.isoformat()
    item = next(p for p in svc.get_churn_radar_scatter().partners if p.partner_id == pid)
    tree = svc.get_partner_referral_tree(pid)
    return {
        "dossier_id": f"dos_{pid}",
        "entity_id": pid,
        "headline": f"{item.name} ({pid})",
        "executive_summary": f"{item.primary_root_cause}. {item.region}, {item.tier.replace('_', ' ').title() if item.tier else ''}.",
        "sections": [
            _risk_section(svc, pid, as_of),
            _signals_section(svc, pid, as_of),
            _integrity_section(tree),
        ],
        "as_of_timestamp": as_of,
        "is_cached_snapshot": False,
        "trade_offs": trade_offs(svc, pid),
    }


def kinetic_canvas(svc: EnginePartnerService, pid: str) -> dict[str, Any]:
    tree = svc.get_partner_referral_tree(pid)
    return {
        "canvas_type": "CHURN_RADAR",
        "payload": {
            "partners": [p.model_dump(mode="json") for p in svc.get_churn_radar_scatter().partners],
            "affiliate_tree": tree,
        },
    }


def case_payload(svc: EnginePartnerService, pid: str) -> dict[str, Any]:
    return {
        "entity_id": pid,
        "active_dossier": active_dossier(svc, pid),
        "kinetic_canvas": kinetic_canvas(svc, pid),
        "data_origin": "engine",
    }
