"""The geo layer of the AML world: additive, deterministic, and its planted truth is separate from what engines read."""

from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from eios.foundry.scenarios.aml_config import STORY_RING_HEAD, STORY_WASH, AmlWorldConfig
from eios.foundry.scenarios.aml_geo import GEO_COLUMNS
from eios.foundry.scenarios.aml_world import AmlWorld, build_aml_world

# Content hashes of the world before the geo layer existed. Geo must not move a single existing byte.
BASELINE = {
    6000: {
        "clients": "d47bccc538e41ffa",
        "transactions": "e40c2201134e3ba2",
        "trades": "cb063c9a769004f7",
        "edges": "7de4397fe2948d5e",
    },
    600: {
        "clients": "bd80754e1b3d63b1",
        "transactions": "206cc3dcb8d791d3",
        "trades": "7e5f8199d302cf0d",
        "edges": "b830d514380ce207",
    },
}


def _hash(frame: pd.DataFrame) -> str:
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=True).values.tobytes()
    ).hexdigest()[:16]


@pytest.fixture(scope="module")
def world() -> AmlWorld:
    return build_aml_world(AmlWorldConfig())


@pytest.mark.parametrize("n_clients", [6000, 600])
def test_the_existing_world_is_byte_identical_with_geo_added(n_clients: int) -> None:
    w = build_aml_world(AmlWorldConfig(n_clients=n_clients))
    assert {
        n: _hash(getattr(w, n)) for n in ("clients", "transactions", "trades", "edges")
    } == BASELINE[n_clients]


def test_geo_flows_have_one_row_per_transaction_and_only_the_geo_columns(world: AmlWorld) -> None:
    flows = world.geo_flows
    assert flows is not None
    assert tuple(flows.columns) == GEO_COLUMNS
    assert flows["txn_id"].tolist() == world.transactions["txn_id"].tolist()
    assert flows["client_id"].tolist() == world.transactions["client_id"].tolist()


def test_the_geo_layer_is_deterministic(world: AmlWorld) -> None:
    again = build_aml_world(AmlWorldConfig())
    assert _hash(again.geo_flows) == _hash(world.geo_flows)
    assert again.truth.geo == world.truth.geo


def _share_foreign_ip(world: AmlWorld, members: frozenset[str]) -> float:
    country = world.clients.set_index("client_id")["country"]
    rows = world.geo_flows[world.geo_flows["client_id"].isin(members)]
    return float((rows["ip_country"] != rows["client_id"].map(country)).mean())


def test_planted_malicious_mismatch_is_every_mule_ring_and_mostly_foreign(world: AmlWorld) -> None:
    geo = world.truth.geo
    assert geo is not None
    assert {STORY_RING_HEAD, "CR73491"} <= geo.mismatch_malicious
    assert geo.mismatch_malicious == frozenset(
        c for ring in world.truth.rings.values() for c in ring
    )
    assert _share_foreign_ip(world, geo.mismatch_malicious) >= 0.7


def test_benign_travellers_and_vpn_users_mismatch_too_but_are_not_malicious(
    world: AmlWorld,
) -> None:
    geo = world.truth.geo
    assert geo is not None
    assert len(geo.travellers) >= 40 and len(geo.privacy_vpn) >= 100
    assert geo.mismatch_benign == geo.travellers | geo.privacy_vpn
    assert not (geo.mismatch_benign & world.truth.malicious())
    # far less foreign than the rings: a trip is a few days, a privacy VPN is used now and then
    assert 0.2 <= _share_foreign_ip(world, geo.mismatch_benign) <= 0.5


def test_everyone_else_rarely_logs_in_from_abroad(world: AmlWorld) -> None:
    geo = world.truth.geo
    assert geo is not None
    others = frozenset(world.clients["client_id"]) - geo.mismatch_malicious - geo.mismatch_benign
    assert _share_foreign_ip(world, others) <= 0.08


def test_risky_corridor_clients_move_money_through_the_planted_hops(world: AmlWorld) -> None:
    geo = world.truth.geo
    assert geo is not None
    assert STORY_WASH in geo.risky_clients
    rows = world.geo_flows[world.geo_flows["client_id"].isin(geo.risky_clients)]
    assert rows["instrument_country"].isin({"MM", "VG"}).mean() >= 0.8
    assert geo.risky_corridors  # (origin, destination) pairs that were actually realised
    assert all(len(pair) == 2 for pair in geo.risky_corridors)


def test_the_geo_frame_carries_no_truth(world: AmlWorld) -> None:
    assert set(world.geo_flows.columns) == set(GEO_COLUMNS)


def test_other_country_never_returns_the_home_country() -> None:
    import numpy as np

    from eios.foundry.scenarios.aml_geo import _other_country

    rng = np.random.default_rng(7)
    home = np.array(["SG", "AE", "NG", "VN"] * 2500)
    for pool in (("SG", "AE"), ("SG", "MY", "ID", "TH", "VN", "AE", "IN", "BR", "CO", "NG")):
        assert (_other_country(rng, home, pool) != home).all()
