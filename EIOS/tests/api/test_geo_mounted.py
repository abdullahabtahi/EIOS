"""The geo and AML graph routes are on the app the container runs, not only on the cockpit module's own app."""

from __future__ import annotations

from eios.api.app import app
from eios.cockpit.geo import GEO_ACCOUNT_PATH, GEO_FLOWS_PATH, GEO_REFERENCE_PATH


def _paths() -> set[str]:
    return set(app.openapi()["paths"])


def test_the_production_api_app_serves_every_geo_route() -> None:
    assert {GEO_REFERENCE_PATH, GEO_FLOWS_PATH, GEO_ACCOUNT_PATH} <= _paths()


def test_the_aml_graph_route_the_workstation_calls_is_on_the_same_app() -> None:
    assert "/api/v1/aml/dossier/{case_id}/graph" in _paths()
