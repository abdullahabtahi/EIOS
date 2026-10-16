"""Login hotspots: countries foreign accounts keep returning to, tested against chance and judged against what was
planted (the rings' exit countries), with and without RL-4 hub suppression."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from eios.dataplane.aml_geo import GeoSnapshot, run_geo_engine
from eios.dataplane.aml_geo_hotspots import FDR, _bh, login_hotspots
from eios.dataplane.geo_evidence import overview
from eios.dataplane.geo_readmodel import curated_tiers
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world

CENTROIDS = Path(__file__).parents[1] / "fixtures" / "geo" / "country_centroids.json"
POSITIONS = {c: (p[0], p[1]) for c, p in json.loads(CENTROIDS.read_text())["positions"].items()}


@pytest.fixture(scope="module")
def snap() -> GeoSnapshot:
    return run_geo_engine(build_aml_world(AmlWorldConfig()), curated_tiers(), POSITIONS)


def test_the_hotspots_are_the_planted_ring_exit_countries_and_rl4_keeps_the_vpn_out(
    snap: GeoSnapshot,
) -> None:
    q = snap.quality.hotspots if snap.quality else None
    assert q is not None
    assert (q.precision, q.recall) == (
        1.0,
        1.0,
    )  # [MEASURED] the six ring-exit countries, nothing else
    assert q.hotspots_without_rl4 == q.hotspots + 1  # the commercial VPN's country, without RL-4
    assert q.precision_without_rl4 < q.precision


def test_one_traveller_logging_in_many_times_does_not_make_a_hotspot() -> None:
    rows = [("c1", "MX", "GW-MX-R01")] * 30 + [(f"c{i}", "MX", "GW-MX-R01") for i in range(2, 30)]
    rows += [(f"d{i}", c, f"GW-{c}-R01") for c in ("PE", "CL", "AR", "BR") for i in range(30)]
    sessions = pd.DataFrame(rows, columns=["client_id", "ip_country", "gateway_id"])
    home = pd.Series("US", index=sessions["client_id"].unique())
    table = login_hotspots(sessions, home)
    assert not table.loc["MX", "hotspot"]  # one returning account in thirty is ordinary


def test_benjamini_hochberg_matches_the_textbook_example() -> None:
    p = pd.Series([0.01, 0.04, 0.03, 0.005], index=list("abcd"))
    q, decided = _bh(p, FDR)
    assert q.round(4).to_dict() == {"a": 0.02, "b": 0.04, "c": 0.04, "d": 0.02}
    assert decided.all()


def test_the_overview_lists_hotspots_with_how_many_countries_were_tested(snap: GeoSnapshot) -> None:
    o = overview(snap)
    assert o["hotspots_tested"] and len(o["login_hotspots"]) == 6
    assert all(h["returning_accounts"] <= h["foreign_accounts"] for h in o["login_hotspots"])
    assert {h["iso2"] for h in o["login_hotspots"]} == {"NG", "IQ", "PK", "TR", "ZA", "AE"}
