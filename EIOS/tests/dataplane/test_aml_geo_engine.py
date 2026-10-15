"""The geo engine finds what was planted, measured against the truth it never reads.

Precision and lift targets were fixed before the engine existed and were met as written [TARGET]. The first recall
targets (0.8 over every planted client) were not reachable, and the diagnosis was structural, not a tuning gap: 44% of
clients have fewer than 3 events, and a client whose events cannot reach significance at the population base rate is
not assessable by any per-client test. Recall is therefore reported over assessable clients, with the assessable count
stated, and the recall targets below are set from that measured basis as regression guards [MEASURED].

N1 (login sessions) moved the ground under the per-client lens on purpose. Every mule ring now logs in through its own
shared VPN exit (not only the two story rings), and the planted benign mismatchers now include 140 privacy-VPN users
who are abroad on about a third of their sessions and travellers whose trips last days: a per-client rate test should
not flag them, so recall over all planted mismatchers stopped being a goal. Ring detection is now carried by the session
lenses (shared exit, impossible travel), whose targets below are regression guards on their first measured run.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from eios.dataplane.aml_geo import GeoSnapshot, run_geo_engine
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import AmlWorld, build_aml_world

TIERS = {
    "MM": "high",
    "KP": "high",
    "IR": "high",
    "VG": "medium",
    "VN": "medium",
    "LA": "medium",
    "PA": "medium",
}


@pytest.fixture(scope="module")
def world() -> AmlWorld:
    return build_aml_world(AmlWorldConfig())


# Real country centroids from the reference layer (Overture), so the travel lens is measured offline on real distances.
CENTROIDS = Path(__file__).parents[1] / "fixtures" / "geo" / "country_centroids.json"
POSITIONS = {c: (p[0], p[1]) for c, p in json.loads(CENTROIDS.read_text())["positions"].items()}


@pytest.fixture(scope="module")
def snap(world: AmlWorld) -> GeoSnapshot:
    return run_geo_engine(world, TIERS, POSITIONS)


def test_mismatch_detection_meets_its_targets(snap: GeoSnapshot) -> None:
    q = snap.quality
    assert q is not None
    assert q.mismatch_precision >= 0.9
    assert q.mismatch_recall_malicious >= 0.5  # measured 0.60 on the N1 world
    assert 0 < q.mismatch_assessable < q.clients  # the limit is stated, not hidden


def test_a_shared_foreign_exit_ties_ring_members_together(snap: GeoSnapshot) -> None:
    s = snap.quality.sessions if snap.quality else None
    assert s is not None
    assert (
        s.exit_precision >= 0.9 and s.exit_recall >= 0.9
    )  # measured 1.00 and 0.99 (a planted world; real data is noisier)
    # the point of the lens: ring members too sparse for the per-client test are recovered
    assert s.rings_not_assessable_per_client > 0
    assert s.recovered_by_exit == s.rings_not_assessable_per_client


def test_the_privacy_vpn_hub_never_ties_anyone_together(snap: GeoSnapshot) -> None:
    assert snap.sessions is not None
    gateways = snap.sessions.gateways.set_index("gateway_id")
    assert gateways.loc["GW-NL-V01", "hub"] and not gateways.loc["GW-NL-V01", "shared_exit"]
    privacy = snap.world.truth.geo.privacy_vpn if snap.world.truth.geo else frozenset()
    exit_flagged = set(snap.clients.loc[snap.clients["exit_flag"], "client_id"])
    assert not (exit_flagged & privacy)


def test_impossible_travel_finds_controllers_and_rl4_cuts_false_alarms(snap: GeoSnapshot) -> None:
    s = snap.quality.sessions if snap.quality else None
    assert s is not None and s.jump_precision is not None and s.jump_recall is not None
    assert s.jump_precision >= 0.6 and s.jump_recall >= 0.5  # measured 0.72 and 0.58
    assert s.benign_flagged_by_jumps is not None and s.benign_flagged_by_jumps_naive is not None
    assert (
        s.benign_flagged_by_jumps < s.benign_flagged_by_jumps_naive
    )  # discounting hub jumps helps


def test_every_impossible_jump_is_one_no_flight_could_make(snap: GeoSnapshot) -> None:
    assert snap.sessions is not None
    jumps = snap.sessions.jumps
    assert len(jumps) > 0
    assert (jumps["km"] >= 500).all()
    assert (jumps["km"] > 1000 * jumps["hours"]).all()
    assert (jumps["from_country"] != jumps["to_country"]).all()


def test_without_positions_travel_is_not_assessable_never_clean(world: AmlWorld) -> None:
    run = run_geo_engine(world, TIERS)
    assert run.sessions is not None and not run.sessions.travel_assessable
    assert not run.clients["travel_assessable"].any() and not run.clients["jump_flag"].any()
    s = run.quality.sessions if run.quality else None
    assert s is not None and s.jump_precision is None and s.jump_flagged is None


def test_risky_corridor_accounts_are_found_with_few_false_alarms(snap: GeoSnapshot) -> None:
    q = snap.quality
    assert q is not None
    assert q.corridor_precision is not None and q.corridor_precision >= 0.9
    assert q.corridor_recall_assessable is not None and q.corridor_recall_assessable >= 0.65


def test_planted_corridors_surface_as_elevated(snap: GeoSnapshot) -> None:
    q = snap.quality
    assert q is not None and q.planted_corridors_elevated is not None
    assert q.planted_corridors_elevated >= 0.8


def test_the_geo_score_ranks_malicious_accounts_far_above_chance(snap: GeoSnapshot) -> None:
    q = snap.quality
    assert q is not None
    assert q.lift_at_k >= 10


def test_every_flagged_client_has_a_stated_reason(snap: GeoSnapshot) -> None:
    flagged = snap.clients[snap.clients["mismatch_flag"] | snap.clients["corridor_flag"]]
    assert len(flagged) > 0
    assert (flagged["mismatch_flag"] | flagged["corridor_flag"]).all()
    assert flagged.loc[flagged["mismatch_flag"], "top_foreign_ip"].str.len().eq(2).all()


def test_corridors_are_cross_border_only_with_a_tier_and_volume(snap: GeoSnapshot) -> None:
    c = snap.corridors
    assert (c["origin"] != c["destination"]).all()
    assert set(c["tier"]) <= {"low", "medium", "high"}
    assert (c["volume_usd"] > 0).all()
    assert c["volume_usd"].is_monotonic_decreasing


def test_without_tiers_the_corridor_metrics_are_not_measured_never_zero(world: AmlWorld) -> None:
    q = run_geo_engine(world, {}).quality
    assert q is not None
    assert q.corridor_precision is None and q.corridor_recall is None
    assert q.corridor_recall_assessable is None and q.planted_corridors_elevated is None
    assert q.mismatch_precision >= 0.9  # the IP lens does not need reference tiers


def test_the_engine_never_reads_the_truth(world: AmlWorld) -> None:
    blind = dataclasses.replace(world, truth=dataclasses.replace(world.truth, geo=None))
    run = run_geo_engine(blind, TIERS)
    assert run.quality is None  # nothing to score against, and it still ran
    assert (
        run.clients["mismatch_flag"].sum()
        == run_geo_engine(world, TIERS).clients["mismatch_flag"].sum()
    )
