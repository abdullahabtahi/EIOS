"""Shared fixtures: the real catalogue over the same services the workstations render."""

import json
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from eios.dataplane.geo_readmodel import StaticGeo, offline_geo
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import build_aml_world
from eios.knowledge.static_index import StaticIndex
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.principal import Principal, principal_for
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort
from eios.warm.sink import LocalWarmSink
from eios.warm.store import LocalWarmStore
from tests.knowledge.passages import ALL

CENTROIDS = Path(__file__).parents[2] / "fixtures" / "geo" / "country_centroids.json"


@cache
def seeded_geo() -> StaticGeo:
    """The seeded world as a geo plane, built once per run: curated tiers, real centroids, the local graph double."""
    positions = {c: (p[0], p[1]) for c, p in json.loads(CENTROIDS.read_text())["positions"].items()}
    return offline_geo(build_aml_world(AmlWorldConfig()), positions)


@pytest.fixture
def port() -> GovernedToolPort:
    warm = LocalWarmStore(
        LocalWarmSink().connection
    )  # the real tables, empty: a history answer is an honest empty one
    return build_port(
        replace(ReadModels.default(), knowledge=StaticIndex(ALL), warm=warm, geo=seeded_geo())
    )


def who(workstation: str) -> Principal:
    return principal_for("uid-test", workstation)
