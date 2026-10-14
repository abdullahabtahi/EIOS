"""The seeded AML world is deterministic, carries the story facts, and plants labelled typologies (spec 031 FR-001..003)."""

import pandas as pd
import pytest

from eios.foundry.scenarios.aml_config import PAYMENT_AGENT_HUB, AmlWorldConfig
from eios.foundry.scenarios.aml_world import AmlWorld, build_aml_world


@pytest.fixture(scope="module")
def world() -> AmlWorld:
    return build_aml_world(AmlWorldConfig())


def test_the_same_config_builds_the_same_world(world: AmlWorld) -> None:
    again = build_aml_world(AmlWorldConfig())
    pd.testing.assert_frame_equal(world.transactions, again.transactions)
    pd.testing.assert_frame_equal(world.trades, again.trades)
    pd.testing.assert_frame_equal(world.edges, again.edges)
    assert world.truth == again.truth


def test_a_different_seed_builds_a_different_world(world: AmlWorld) -> None:
    other = build_aml_world(AmlWorldConfig(seed=7))
    assert not world.transactions["amount"].equals(other.transactions["amount"])


def test_client_ids_are_unique_and_sized_to_the_config(world: AmlWorld) -> None:
    assert len(world.clients) == world.config.n_clients
    assert world.clients["client_id"].is_unique


def test_the_story_ring_head_has_the_documented_facts(world: AmlWorld) -> None:
    row = world.clients.set_index("client_id").loc["CR84920"]
    assert row["declared_monthly_income_usd"] == 500.0
    txns = world.transactions[world.transactions["client_id"] == "CR84920"]
    deposits = txns[txns["transaction_type"] == "DEPOSIT"]
    assert len(deposits) == 16
    assert set(deposits["amount"]) == {500.0}
    assert set(deposits["asset"]) == {"USDT"}
    pending = txns[(txns["transaction_type"] == "WITHDRAWAL") & (txns["status"] == "PENDING")]
    assert pending["amount"].tolist() == [7800.0]
    gap = pending["timestamp"].iloc[0] - deposits["timestamp"].max()
    assert gap == pd.Timedelta(hours=2)


def test_the_story_rings_have_the_documented_sizes(world: AmlWorld) -> None:
    sizes = sorted(len(m) for m in world.truth.rings.values())
    assert 23 in sizes and 8 in sizes
    assert "CR84920" in world.truth.rings["RING-14"]
    assert "CR73491" in world.truth.rings["RING-22"]
    assert len(world.truth.rings["RING-14"]) == 23


def test_the_story_wash_account_withdraws_twelve_minutes_after_depositing(world: AmlWorld) -> None:
    txns = world.transactions[world.transactions["client_id"] == "CR91204"]
    deposit = txns[txns["transaction_type"] == "DEPOSIT"].iloc[0]
    withdrawal = txns[txns["transaction_type"] == "WITHDRAWAL"].iloc[0]
    assert withdrawal["timestamp"] - deposit["timestamp"] == pd.Timedelta(minutes=12)
    assert withdrawal["status"] == "PENDING" and withdrawal["reference"] == "W-91204-1"


def test_wash_accounts_net_to_almost_nothing(world: AmlWorld) -> None:
    wash = [c for c, tags in world.truth.tags.items() if "WASH_ROUND_TRIP" in tags]
    assert len(wash) == world.config.n_wash + 1
    net = (
        world.trades[world.trades["client_id"].isin(wash)].groupby("client_id")["profit_loss"].sum()
    )
    assert (net.abs() <= 0.05).all()


def test_the_payment_agent_and_cgnat_gateways_are_hubs(world: AmlWorld) -> None:
    degree = world.edges.groupby("target_id")["source_id"].nunique()
    assert degree[PAYMENT_AGENT_HUB] == world.config.n_hub_agent_clients
    cgnat = world.edges[world.edges["is_shared_context"]]
    sizes = cgnat.groupby("target_id")["source_id"].nunique()
    assert len(sizes) == world.config.n_cgnat_hubs
    assert (sizes > 100).all()


def test_private_ring_tokens_stay_below_the_hub_limit(world: AmlWorld) -> None:
    ring_tokens = world.edges[world.edges["target_id"].str.contains("_ring_|tok_dev|tok_pay")]
    degree = ring_tokens.groupby("target_id")["source_id"].nunique()
    assert (degree <= 100).all()


def test_the_truth_table_names_malicious_clients_and_leaves_hard_negatives_out(
    world: AmlWorld,
) -> None:
    bad = world.truth.malicious()
    assert {"CR84920", "CR91204", "CR73491"} <= bad
    scalpers_and_hubs = [c for c, t in world.truth.tags.items() if t == ("CGNAT_GATEWAY",)]
    assert scalpers_and_hubs and not (set(scalpers_and_hubs) & bad)
