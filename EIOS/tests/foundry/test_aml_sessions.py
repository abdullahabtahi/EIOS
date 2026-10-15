"""Login sessions of the AML world: consistent with the transactions, and the planted behaviour is what it claims."""

from __future__ import annotations

import pandas as pd
import pytest

from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_sessions import SESSION_COLUMNS, TRIP_BUFFER
from eios.foundry.scenarios.aml_world import AmlWorld, build_aml_world


@pytest.fixture(scope="module")
def world() -> AmlWorld:
    return build_aml_world(AmlWorldConfig())


@pytest.fixture(scope="module")
def sessions(world: AmlWorld) -> pd.DataFrame:
    assert world.geo_sessions is not None
    return world.geo_sessions


def test_every_transaction_is_made_in_a_session_from_the_same_country(
    world: AmlWorld, sessions: pd.DataFrame
) -> None:
    assert tuple(sessions.columns) == SESSION_COLUMNS
    made = sessions.dropna(subset=["txn_id"]).set_index("txn_id")["ip_country"]
    assert len(made) == len(world.transactions)
    flows = world.geo_flows.set_index("txn_id")["ip_country"]
    assert (made.loc[flows.index] == flows).all()
    assert len(sessions) > len(world.transactions)  # clients also log in without transacting
    assert sessions["session_id"].is_unique


def test_a_gateway_sits_in_the_country_its_sessions_come_from(sessions: pd.DataFrame) -> None:
    assert (sessions["gateway_id"].str.slice(3, 5) == sessions["ip_country"]).all()


def test_each_ring_logs_in_through_its_own_shared_exit(
    world: AmlWorld, sessions: pd.DataFrame
) -> None:
    geo = world.truth.geo
    assert geo is not None and len(geo.ring_exits) == len(world.truth.rings)
    for exit_id, members in geo.ring_exits.items():
        users = set(sessions.loc[sessions["gateway_id"] == exit_id, "client_id"])
        assert users <= members  # nobody outside the ring uses it
        assert len(users) >= 0.9 * len(members)


def test_a_trip_is_one_block_abroad_with_no_session_near_its_ends(
    world: AmlWorld, sessions: pd.DataFrame
) -> None:
    geo = world.truth.geo
    assert geo is not None
    home = world.clients.set_index("client_id")["country"]
    for client in sorted(geo.travellers):
        mine = sessions[sessions["client_id"] == client]
        abroad = mine[mine["ip_country"] != home[client]]
        assert abroad["ip_country"].nunique() == 1
        lo, hi = abroad["ts"].min(), abroad["ts"].max()
        at_home = mine[mine["ip_country"] == home[client]]["ts"]
        assert not ((at_home > lo) & (at_home < hi)).any()  # one contiguous trip
        assert not ((at_home > lo - TRIP_BUFFER) & (at_home < lo)).any()
        assert not ((at_home > hi) & (at_home < hi + TRIP_BUFFER)).any()


def test_the_privacy_vpn_is_a_hub_shared_by_more_than_the_rl4_line(
    world: AmlWorld, sessions: pd.DataFrame
) -> None:
    geo = world.truth.geo
    assert geo is not None
    users = sessions.loc[sessions["gateway_id"] == "GW-NL-V01", "client_id"].nunique()
    assert users > 100
    assert not (geo.privacy_vpn & world.truth.malicious())


def test_sessions_are_deterministic_and_carry_no_truth(
    world: AmlWorld, sessions: pd.DataFrame
) -> None:
    again = build_aml_world(AmlWorldConfig()).geo_sessions
    assert again is not None
    pd.testing.assert_frame_equal(again, sessions)
    assert not {"truth", "malicious", "ring", "traveller"} & {c.lower() for c in sessions.columns}
