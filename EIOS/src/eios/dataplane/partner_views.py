"""Partner API views over the engine plane: cohorts, the partner object, deal cards, the what-if and trading pairs.

Each replaces a canned payload in `api/routes_churn.py` or `api/routes_fraud.py`. Nothing here is model-written
prose: the what-if is the hazard model's counterfactual and says so, and deal cards carry no scripted messages.
"""

from __future__ import annotations

import re
from typing import Any

from eios.dataplane.partner_engine import HIGH_RISK
from eios.dataplane.partner_playbooks import FAST_PATH_BUDGET_USD, PROJECTION_BASIS, playbooks_for
from eios.dataplane.partner_service import EnginePartnerService

EVALUATOR = "DiscreteTimeHazardModel counterfactual"
_INTENSITY = re.compile(r"intensity:\s*(\d{1,3})\s*%")
_PCT = 100.0


def cohorts(svc: EnginePartnerService) -> dict[str, Any]:
    """Regions whose share of high-risk partners is significant under the binomial test."""
    snap = svc.snapshot
    radar = {p.partner_id: p for p in svc.get_churn_radar_scatter().partners}
    out = []
    for alert in snap.cohorts:
        members = [radar[p] for p in alert.affected_partner_ids if p in radar]
        hazards = sorted(p.churn_hazard_probability for p in members)
        logins = sorted(p.login_decay_pct for p in members)
        out.append(
            {
                "cohort_id": alert.alert_id,
                "region": alert.region_id,
                "partner_count": alert.partner_count,
                "aggregate_value_at_risk_usd": alert.aggregate_value_at_risk_usd,
                "median_hazard": hazards[len(hazards) // 2] if hazards else None,
                "login_decay_median_pct": logins[len(logins) // 2] if logins else None,
                "p_value": alert.p_value,
                "primary_driver": alert.common_driver,
                "recommended_intervention": alert.recommended_playbook,
                "affected_partner_ids": alert.affected_partner_ids,
                "status": "ALERT",
            }
        )
    return {"as_of": svc.as_of.isoformat(), "cohorts": out, "test": "binomial tail, alpha 0.05"}


def ontology_360(svc: EnginePartnerService, ref: str) -> dict[str, Any]:
    """The partner as an ontology object: computed properties, links to what it touches, and its allowed actions."""
    pid = svc.resolve(ref)
    item = next(p for p in svc.get_churn_radar_scatter().partners if p.partner_id == pid)
    ev = svc.evidence(pid)
    tree = svc.get_partner_referral_tree(pid)
    deals = svc.get_retention_playbooks(pid)
    return {
        "object_type": "Partner",
        "primary_key": pid,
        "security_markings": ["COMMERCIAL_SENSITIVE"],
        "lifecycle_state": "AT_RISK" if item.churn_hazard_probability >= HIGH_RISK else "ACTIVE",
        "as_of": svc.as_of.isoformat(),
        "properties": {
            "partner_id": pid,
            "name": item.name,
            "tier": item.tier,
            "market": item.region,
            "cohort": item.cohort,
            "realized_volume_30d_usd": item.realized_volume_30d_usd,
            "hazard_probability_30d": item.churn_hazard_probability,
            "days_to_intervention_deadline": item.days_to_intervention_deadline,
            "login_decay_pct": item.login_decay_pct,
            "ftd_decay_pct": item.ftd_decay_pct,
            "payout_latency_hours": ev.payout_latency_hours,
            "baseline_payout_latency_hours": ev.baseline_latency_hours,
        },
        "links": [
            {"link_type": "HAS_SUB_AFFILIATE", "target_type": "Partner", "count": len(tree["sub_affiliates"]),
             "summary": f"{tree['active_sub_affiliates_count']} active in the last two weeks"},
            {"link_type": "REFERRED_CLIENTS", "target_type": "ClientAccount", "count": tree["referred_client_count"],
             "summary": f"{len(tree['aml_exposure'])} in prioritised AML cases"},
            {"link_type": "HAS_MESSAGES", "target_type": "PartnerMessage", "count": len(svc.get_messages(pid)),
             "summary": f"{ev.negative_messages} negative"},
            {"link_type": "OPPOSITE_TRADING_PAIR", "target_type": "TradingPair", "count": len(tree["detected_abusive_rings"]),
             "summary": "across this partner and its sub-affiliates"},
        ],
        "upstream_lineage": [
            "partner_engagement_signals", "partner_comms", "commission_ledger", "partner_360",
            "ChurnRadarPipeline", "ChurnSignalExplainer", "TimeBucketedPairDetector",
        ],
        "allowed_action_types": [
            {"action_type": d.action_type, "label": d.title, "parameters": {"budget_usd": d.estimated_cost_usd},
             "requires_four_eyes": d.requires_four_eyes}
            for d in deals
        ],
    }  # fmt: skip


def battlecards(svc: EnginePartnerService, ref: str) -> dict[str, Any]:
    """Retention options as cards: what each costs and what the hazard model projects. No drafted messages."""
    pid = svc.resolve(ref)
    row, cf = svc.row(pid), svc.counterfactual()
    cards = []
    for pb in playbooks_for(svc.evidence(pid)):
        p = cf.project(row, pb)
        cards.append(
            {
                "id": pb.playbook_id,
                "title": pb.title,
                "action_type": pb.action_type,
                "projected_lift_pct": p.uplift_pct,
                "deal_cost_usd": p.cost_usd,
                "net_margin_usd": p.net_margin_usd,
                "requires_four_eyes": p.cost_usd > FAST_PATH_BUDGET_USD,
                "basis": PROJECTION_BASIS,
            }
        )
    return {
        "partner_id": pid,
        "synthesizer_model": None,
        "generated_at": svc.as_of.isoformat(),
        "battlecards": cards,
    }


def _intensity(prompt: str) -> float:
    found = _INTENSITY.search(prompt)
    return min(int(found.group(1)), 100) / _PCT if found else 1.0


def what_if(svc: EnginePartnerService, ref: str, prompt: str) -> dict[str, Any]:
    """The partner's best playbook at the asked intensity, re-scored by the hazard model."""
    pid = svc.resolve(ref)
    row, cf = svc.row(pid), svc.counterfactual()
    options = playbooks_for(svc.evidence(pid))
    intensity = _intensity(prompt)
    base = {
        "partner_id": pid,
        "evaluator_model": EVALUATOR,
        "evaluated_at": svc.as_of.isoformat(),
        "query_prompt": prompt,
    }
    if not options:
        return {**base, "verdict": "NO_PLAYBOOK", "governed_decision_rationale": "No retention playbook applies to this partner's signals.",
                "projected_retention_lift_pct": None, "estimated_deal_cost_usd": None, "projected_net_margin_usd": None,
                "confidence_interval_95": None, "causal_refuter_p_value": None}  # fmt: skip
    pb, p = max(
        ((pb, cf.project(row, pb, intensity)) for pb in options), key=lambda t: t[1].net_margin_usd
    )
    verdict = "NET_POSITIVE" if p.net_margin_usd > 0 else "MARGIN_DILUTIVE"
    rationale = (
        f"{pb.title} at {intensity:.0%}: hazard {p.hazard_now:.0%} to {p.hazard_after:.0%}, cost ${p.cost_usd:,.0f}, "
        f"net ${p.net_margin_usd:,.0f} over a quarter. {PROJECTION_BASIS}."
    )
    return {
        **base,
        "playbook_id": pb.playbook_id,
        "projected_retention_lift_pct": p.uplift_pct,
        "confidence_interval_95": None,  # the model gives a point projection; no interval is claimed
        "estimated_deal_cost_usd": p.cost_usd,
        "projected_net_margin_usd": p.net_margin_usd,
        "verdict": verdict,
        "governed_decision_rationale": rationale,
        "causal_refuter_p_value": None,  # not a causal estimate (RL-3)
    }


def pairs(svc: EnginePartnerService) -> dict[str, Any]:
    roster = svc.snapshot.world.roster.set_index("partner_id")
    parent = roster["parent_id"].to_dict()
    return {
        "as_of": svc.as_of.isoformat(),
        "monitored_pairs_count": len(svc.snapshot.pairs),
        "active_collusion_rings": [
            {
                "ring_id": p.pair_id,
                "master_affiliate": parent.get(p.partner_a) or p.partner_a,
                "account_a": p.account_a,
                "account_b": p.account_b,
                "partner_a": p.partner_a,
                "partner_b": p.partner_b,
                "instrument": p.symbol,
                "co_occurrences": p.co_occurrence_count,
                "timing_within_15s_pct": p.timing_correlation_pct,
                "collusion_confidence": p.collusion_confidence,
                "commission_extracted_usd": p.total_commission_extracted_usd,
                "status": "FLAGGED",
            }
            for p in svc.snapshot.pairs
        ],
    }
