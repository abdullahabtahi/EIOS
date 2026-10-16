"""A figure the geo assistant showed can be derived again from its fact id, through the same port (the replay check)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from eios.assistant.tools import expand_fact_ids
from eios.ontology.omcp.port.catalogue import build_port
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.service import GovernedToolPort
from tests.ontology.port.conftest import seeded_geo, who

GEO = who("geospatial")


@pytest.fixture(scope="module")
def models() -> ReadModels:
    return replace(ReadModels.default(), geo=seeded_geo())


@pytest.fixture(scope="module")
def geo_port(models: ReadModels) -> GovernedToolPort:
    return build_port(models)  # binds `models.facts` to this port


def _value_at(payload: Any, path: str) -> float:
    node = payload
    for part in path.replace("]", "").replace("[", ".").split("."):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return float(node)


@pytest.mark.parametrize(
    ("tool", "args", "path"),
    [
        ("get_shared_exit", {"gateway_id": "GW-NG-X00"}, "flagged_accounts"),
        ("get_shared_exit", {"gateway_id": "GW-NG-X00"}, "ring.graph_users"),
        ("get_corridor", {"corridor_id": "ID>MM"}, "volume_usd"),
        ("get_jurisdiction", {"country_id": "IQ"}, "login_accounts"),
        ("get_list_change_impact", {"list_id": "fatf"}, "added.countries[0].sessions"),
        ("list_geo_leads", {"kind": "shared_exit"}, "exits[1].accounts"),
        ("get_geo_overview", {}, "lenses[0].flagged"),
    ],
)
def test_a_shown_geo_figure_resolves_again_to_the_same_value(
    models: ReadModels, geo_port: GovernedToolPort, tool: str, args: dict[str, str], path: str
) -> None:
    payload = geo_port.call(GEO, tool, args).payload()
    fact_id = expand_fact_ids(payload)["fact_ids"][path]
    again = models.facts.resolve(GEO, fact_id)
    assert again.value == _value_at(payload, path) and again.unit


@pytest.mark.parametrize(
    "fact_id",
    ["geo.exit:GW-NG-X00:country.name", "geo.exit:GW-NG-X00:ring.linked[99].account_id"],
)
def test_a_path_that_is_no_figure_is_not_found(
    models: ReadModels, geo_port: GovernedToolPort, fact_id: str
) -> None:
    with pytest.raises(PortError) as exc:
        models.facts.resolve(GEO, fact_id)
    assert exc.value.error.code is ToolErrorCode.NOT_FOUND


def test_another_workstation_cannot_resolve_a_geo_figure(
    models: ReadModels, geo_port: GovernedToolPort
) -> None:
    with pytest.raises(PortError) as exc:
        models.facts.resolve(who("partner_manager"), "geo.exit:GW-NG-X00:flagged_accounts")
    assert exc.value.error.code is ToolErrorCode.FORBIDDEN_ROLE
