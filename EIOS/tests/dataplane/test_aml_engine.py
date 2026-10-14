"""The AML engine runs the real detectors over the seeded world and is measured against the truth (spec 031 FR-004..006)."""

import pytest

from eios.dataplane.aml_engine import AmlSnapshot, run_aml_engine
from eios.foundry.scenarios.aml_config import PAYMENT_AGENT_HUB, AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world


@pytest.fixture(scope="module")
def snapshot() -> AmlSnapshot:
    return run_aml_engine(build_aml_world(AmlWorldConfig()))


def test_raw_alerts_compress_to_a_ranked_queue_of_fifty(snapshot: AmlSnapshot) -> None:
    q = snapshot.quality
    assert 1200 <= q.raw_alerts <= 3000  # the brief's order of magnitude, not a constant
    assert q.cases < q.raw_alerts
    assert q.top_k == 50
    assert [c.rank for c in snapshot.cases[:3]] == [1, 2, 3]


def test_planted_accounts_are_found_and_ranked(snapshot: AmlSnapshot) -> None:
    q = snapshot.quality
    assert q.recall_any_alert >= 0.99  # every planted account raises at least one alert
    assert q.recall_at_k >= 0.9  # and almost all sit in the fifty a human reviews
    assert q.hits_at_k >= 30 and q.hits_at_k <= q.planted_cases


def test_every_planted_ring_is_recovered_without_merging_the_world(snapshot: AmlSnapshot) -> None:
    q = snapshot.quality
    assert q.ring_recovery >= 0.95
    assert q.largest_cluster == max(len(m) for m in snapshot.world.truth.rings.values())


def test_hub_nodes_are_suppressed_out_of_every_cluster(snapshot: AmlSnapshot) -> None:
    tokens = {
        t
        for c in snapshot.clusters
        for t in (*c.shared_payment_tokens, *c.shared_device_tokens, *c.shared_ip_tokens)
    }
    assert PAYMENT_AGENT_HUB not in tokens
    assert not any(t.startswith("tok_ip_") and "cgnat" in t for t in tokens)


def test_the_story_rings_lead_with_their_first_mover(snapshot: AmlSnapshot) -> None:
    head = snapshot.case_for("CR84920")
    assert (
        head is not None and head.client_id == "CR84920" and head.ring_size == 23 and head.rank == 1
    )
    device = snapshot.case_for("CR73491")
    assert device is not None and device.client_id == "CR73491" and device.ring_size == 8
    wash = snapshot.case_for("CR91204")
    assert wash is not None and wash.in_top_k and "ROUND_TRIP" in wash.rules


def test_a_ring_is_one_case_and_each_member_resolves_to_it(snapshot: AmlSnapshot) -> None:
    case = snapshot.case_for("CR84920")
    assert case is not None and len(case.members) == 23
    assert all(snapshot.case_for(m) is case for m in case.members)
    assert len({c.client_id for c in snapshot.cases}) == len(snapshot.cases)


def test_alert_features_come_from_data_not_constants(snapshot: AmlSnapshot) -> None:
    for name in ("peer_z_score", "hours_since_kyc", "deposit_withdrawal_ratio", "market_risk_pct"):
        values = {round(float(a.attributes[name]), 3) for a in snapshot.alerts}
        assert len(values) > 50, name


def test_the_build_is_deterministic(snapshot: AmlSnapshot) -> None:
    again = run_aml_engine(build_aml_world(AmlWorldConfig()))
    assert [(c.client_id, c.risk) for c in again.cases[:60]] == [
        (c.client_id, c.risk) for c in snapshot.cases[:60]
    ]
    assert {c.cluster_id for c in again.clusters} == {c.cluster_id for c in snapshot.clusters}
