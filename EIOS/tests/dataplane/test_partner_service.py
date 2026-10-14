"""The engine-backed partner read model and its views (spec 032 FR-007, FR-010 to FR-012)."""

import re

import pytest

from eios.cockpit import partner_engine_view as view
from eios.dataplane import partner_views
from eios.dataplane.partner_playbooks import FAST_PATH_BUDGET_USD, PROJECTION_BASIS
from eios.dataplane.partner_service import EnginePartnerService, UnknownPartnerError
from eios.foundry.scenarios.partner_config import STORY_PARTNER


def test_the_radar_is_ranked_by_expected_loss_and_meets_its_contract(
    partner_service: EnginePartnerService,
) -> None:
    radar = partner_service.get_churn_radar_scatter()
    assert len(radar.partners) == 240
    payload = radar.to_contract_dict()  # validates against churn-radar-scatter
    assert payload["partners"][0]["partner_id"] == radar.partners[0].partner_id
    losses = [p.churn_hazard_probability * p.realized_volume_30d_usd for p in radar.partners]
    assert losses[0] >= losses[-1]


def test_root_causes_are_words_only_so_figures_come_from_fields(
    partner_service: EnginePartnerService,
) -> None:
    for p in partner_service.get_churn_radar_scatter().partners:
        assert not re.search(r"\d", p.primary_root_cause), p.primary_root_cause


def test_the_story_partner_shows_what_its_rows_say(partner_service: EnginePartnerService) -> None:
    p = next(
        p
        for p in partner_service.get_churn_radar_scatter().partners
        if p.partner_id == STORY_PARTNER
    )
    ev = partner_service.evidence(STORY_PARTNER)
    assert p.churn_hazard_probability >= 0.5 and p.quadrant.value.endswith("HIGH_RISK")
    assert (
        p.primary_driver == "OPERATIONAL_CASHIER"
        and ev.payout_latency_hours > ev.baseline_latency_hours
    )
    assert p.login_decay_pct < 0 and p.support_ticket_count and p.support_ticket_count >= 2
    assert (
        p.historical_drift
        and p.historical_drift["tMinus30d"]["pChurn"] < p.churn_hazard_probability
    )
    assert p.empirical_win_rate is None  # no playbook outcome history exists, so none is claimed


def test_aliases_resolve_and_unknown_partners_are_refused(
    partner_service: EnginePartnerService,
) -> None:
    assert partner_service.resolve("AP-1029") == STORY_PARTNER
    assert partner_service.resolve("ptr-882") == STORY_PARTNER
    with pytest.raises(UnknownPartnerError):
        partner_service.resolve("PTR-0000")


def test_deals_follow_the_fast_path_rule_and_never_raise_hazard(
    partner_service: EnginePartnerService,
) -> None:
    deals = partner_service.get_retention_playbooks(STORY_PARTNER)
    assert deals and deals[0].action_type == "WhitelistDirectCashierRail"
    for d in deals:
        assert d.requires_four_eyes is (d.estimated_cost_usd > FAST_PATH_BUDGET_USD)
        assert d.is_fast_path_eligible is not d.requires_four_eyes
        assert 0.0 <= d.projected_retention_uplift_pct <= 100.0


def test_the_referral_tree_reports_pairs_across_the_partner_network(
    partner_service: EnginePartnerService,
) -> None:
    tree = partner_service.get_partner_referral_tree(STORY_PARTNER)
    kids = {s["id"] for s in tree["sub_affiliates"]}
    assert tree["detected_abusive_rings"], "the story partner's network holds a planted pair"
    for ring in tree["detected_abusive_rings"]:
        assert set(ring["partners"]) <= kids | {STORY_PARTNER}
        assert ring["matched_timing_seconds"] < 5.0
    assert (
        tree["referred_client_count"] == 0 and tree["aml_exposure"] == []
    )  # no AML world attached here


def test_messages_come_from_the_world_for_any_partner(
    partner_service: EnginePartnerService,
) -> None:
    other = partner_service.get_churn_radar_scatter().partners[5].partner_id
    assert partner_service.has_detail(other)
    msgs = partner_service.get_messages(STORY_PARTNER)
    assert any(m.topic == "payout_delay" for m in msgs)
    assert [m.received_at for m in msgs] == sorted(m.received_at for m in msgs)


def test_the_what_if_is_a_labelled_projection_that_grows_with_intensity(
    partner_service: EnginePartnerService,
) -> None:
    low = partner_views.what_if(partner_service, STORY_PARTNER, "Simulate deal (intensity: 20%)")
    high = partner_views.what_if(partner_service, STORY_PARTNER, "Simulate deal (intensity: 100%)")
    assert 0 <= low["projected_retention_lift_pct"] <= high["projected_retention_lift_pct"]
    assert high["causal_refuter_p_value"] is None and high["confidence_interval_95"] is None
    assert (
        "Gemini" not in high["evaluator_model"]
        and PROJECTION_BASIS in high["governed_decision_rationale"]
    )


def test_cards_and_cohorts_are_computed(partner_service: EnginePartnerService) -> None:
    cards = partner_views.battlecards(partner_service, STORY_PARTNER)
    assert cards["synthesizer_model"] is None and all(
        "whatsapp_script" not in c for c in cards["battlecards"]
    )
    (cohort,) = partner_views.cohorts(partner_service)["cohorts"]
    assert cohort["region"] == "SEA" and cohort["p_value"] < 0.05
    stage = cohort["stage_request"]
    assert stage["action_type"] == "LaunchRetentionPlaybook" and stage["metadata"]["partner_ids"]
    assert stage["metadata"]["budget"] >= 0
    assert partner_views.pairs(partner_service)["monitored_pairs_count"] == 6


def test_the_workstation_payload_opens_any_partner_with_stageable_deals(
    partner_service: EnginePartnerService,
) -> None:
    now = partner_service.as_of.isoformat()
    items = view.triage_items(partner_service, now)
    assert len(items) == view.QUEUE_LIMIT and items[0]["entity_type"] == "PARTNER"
    case = view.case_payload(partner_service, STORY_PARTNER)
    dossier = case["active_dossier"]
    assert [s["section_id"] for s in dossier["sections"]] == [
        "sec_risk",
        "sec_signals",
        "sec_integrity",
    ]
    (stage, *_) = [t["stageRequest"] for t in dossier["trade_offs"]]
    assert (
        stage["action_type"] == "WhitelistDirectCashierRail"
        and stage["metadata"]["partner_id"] == STORY_PARTNER
    )
    assert case["kinetic_canvas"]["payload"]["affiliate_tree"]["master_partner_id"] == STORY_PARTNER
