"""EngineAMLService answers for any account in the world, validates against the cockpit contracts, and agrees with itself (spec 031 FR-007, FR-012)."""

import pytest

from eios.dataplane.aml_engine import run_aml_engine
from eios.dataplane.aml_service import (
    CORRELATION_ONLY,
    EngineAMLService,
    UnknownAccountError,
    normalize_ref,
)
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world


@pytest.fixture(scope="module")
def service() -> EngineAMLService:
    return EngineAMLService(run_aml_engine(build_aml_world(AmlWorldConfig())))


def test_the_queue_is_ranked_and_in_the_fixture_shape(service: EngineAMLService) -> None:
    queue = service.get_triage_queue(min_score=0, limit=50)
    assert len(queue) == 50
    assert set(queue[0]) == {
        "alert_id",
        "entity_id",
        "risk_score",
        "discrepancy_summary",
        "syndicate_size",
        "age_hours",
        "status",
    }
    scores = [q["risk_score"] for q in queue]
    assert scores == sorted(scores, reverse=True)
    assert queue[0]["entity_id"] == "CR84920" and queue[0]["syndicate_size"] == 23


def test_the_story_headline_states_the_discrepancy(service: EngineAMLService) -> None:
    rows = {r["entity_id"]: r for r in service.get_triage_cases(0, 100)}
    assert (
        "Deposits" in rows["CR84920"]["discrepancy_summary"]
        or "linked accounts" in rows["CR84920"]["discrepancy_summary"]
    )
    assert rows["CR91204"]["discrepancy_summary"].startswith("Round-trip")


def test_dossiers_validate_against_the_contract_for_many_accounts(
    service: EngineAMLService,
) -> None:
    for row in service.get_triage_cases(0, 12):
        dossier = service.get_entity_dossier(row["entity_id"])
        contract = dossier.to_contract_dict()  # raises when the JSON schema is violated
        assert contract["composite_risk_score"] == row["risk_score"]


def test_the_story_dossier_has_the_documented_facts(service: EngineAMLService) -> None:
    d = service.get_entity_dossier("CR84920")
    assert d.kyc.declared_monthly_income_usd == 500.0
    assert d.discrepancy.realized_deposit_volume_30d_usd == 8000.0
    assert d.discrepancy.discrepancy_multiplier == 16.0
    assert d.discrepancy.crypto_usdt_deposit_ratio == 1.0
    assert d.syndicate_ring_size == 23


def test_different_accounts_get_different_dossiers(service: EngineAMLService) -> None:
    a, b = service.get_triage_cases(0, 2)
    da, db = service.get_entity_dossier(a["entity_id"]), service.get_entity_dossier(b["entity_id"])
    assert da.identity_cluster_key != db.identity_cluster_key
    assert (
        da.discrepancy.realized_deposit_volume_30d_usd
        != db.discrepancy.realized_deposit_volume_30d_usd
    )


def test_an_unknown_account_is_not_invented(service: EngineAMLService) -> None:
    with pytest.raises(UnknownAccountError):
        service.get_entity_dossier("CR00000")
    assert not service.supports_detail("CR00000")


def test_the_graph_collapses_the_hub_and_the_ring_and_validates(service: EngineAMLService) -> None:
    graph = service.get_kinetic_network_graph("CR84920")
    contract = graph.to_contract_dict()
    hub = next(n for n in graph.nodes if n.node_id == "PA-HUB-007")
    assert hub.is_hub_suppressed and hub.degree == 142
    ring = next(n for n in graph.nodes if n.node_type.value == "COLLAPSED_CLUSTER_HUB")
    assert ring.collapsed_node_count == 22
    assert contract["total_uncollapsed_entities"] >= 23
    assert any(
        e["matched_timing_seconds"] is not None and e["matched_timing_seconds"] < 2
        for e in contract["edges"]
    )


def test_a_lone_account_has_a_small_honest_graph(service: EngineAMLService) -> None:
    lone = next(
        r["entity_id"] for r in service.get_triage_cases(0, 200) if r["syndicate_size"] == 1
    )
    graph = service.get_kinetic_network_graph(lone)
    assert graph.seed_entity_id == lone and all(
        n.node_type.value != "COLLAPSED_CLUSTER_HUB" for n in graph.nodes
    )


def test_the_sar_draft_validates_and_carries_computed_numbers(service: EngineAMLService) -> None:
    sar = service.compose_sar_draft(entity_id="CR84920", investigator_id="INV-9").to_contract_dict()
    assert "8,000.00" in sar["narrative_summary"] and "16.0x" in sar["narrative_summary"]
    assert sar["investigator_id"] == "INV-9" and sar["subject_entity_id"] == "CR84920"


def test_timeline_and_pending_withdrawal_come_from_events(service: EngineAMLService) -> None:
    events = service.get_activity_timeline("CR84920") or []
    kinds = [e.kind for e in events]
    assert kinds.count("DEPOSIT") == 16 and "RING_LINK" in kinds and "WITHDRAWAL_REQUESTED" in kinds
    pending = service.get_pending_withdrawal("CR84920")
    assert (
        pending is not None
        and pending.withdrawal_id == "W-84920-1"
        and pending.amount_usd == 7800.0
    )
    assert pending.hours_since_deposit == 2.0
    wash = service.get_pending_withdrawal("CR91204")
    assert wash is not None and wash.hours_since_deposit == 0.2 and wash.market_risk_pct < 0.001


def test_the_causal_label_follows_the_refuter(service: EngineAMLService) -> None:
    view = service.get_case_view("CR84920")
    verdict = service.snapshot.ring_refutation.gate_verdict
    assert (view["causal_label"] == "Verified causal") == (verdict == "PASS")
    lone = next(
        r["entity_id"] for r in service.get_triage_cases(0, 200) if r["syndicate_size"] == 1
    )
    assert service.get_case_view(lone)["causal_label"] == CORRELATION_ONLY


def test_case_references_normalise() -> None:
    assert {normalize_ref(x) for x in ("case_aml_CR84920", "ALT-CR84920", "cr84920", "84920")} == {
        "CR84920"
    }
