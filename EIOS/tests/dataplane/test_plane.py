"""One data plane per process: `EIOS_DATA_PLANE` picks it, every consumer shares it (spec 031 FR-008, FR-009)."""

from collections.abc import Iterator

import pytest

from eios.dataplane import plane
from eios.dataplane.plane import PlaneConfigError, PlaneKind, plane_kind
from eios.ontology.omcp.port.contracts import DataOrigin


@pytest.fixture(autouse=True)
def _fresh_plane() -> Iterator[None]:
    plane.reset_for_testing()
    yield
    plane.reset_for_testing()


def test_the_default_plane_is_the_engine_and_the_choice_is_validated() -> None:
    assert plane_kind({}) is PlaneKind.ENGINE
    assert plane_kind({"EIOS_DATA_PLANE": " Fixture "}) is PlaneKind.FIXTURE
    with pytest.raises(PlaneConfigError, match="engine"):
        plane_kind({"EIOS_DATA_PLANE": "warehouse"})


def test_the_fixture_plane_has_no_engine_and_labels_its_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIOS_DATA_PLANE", "fixture")
    models = plane.read_models()
    assert plane.engine_service() is None
    assert models.aml_origin is DataOrigin.FIXTURE
    assert plane.aml_data_origin() == "fixture"


def test_every_caller_gets_the_same_read_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EIOS_DATA_PLANE", "fixture")
    assert plane.read_models() is plane.read_models()


def test_the_engine_plane_builds_once_and_serves_every_account_it_holds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EIOS_DATA_PLANE", "engine")
    models = plane.read_models()
    engine = plane.engine_service()
    assert engine is not None and models.aml is engine
    assert models.aml_origin is DataOrigin.ENGINE and plane.aml_data_origin() == "engine"
    assert models.clock() == engine.as_of  # the clock is the world's as-of, never the wall clock
    assert models.directory.resolve("CR84920").entity_id == "CR84920"
    some = engine.account_ids()[500]
    assert models.directory.resolve(some).entity_id == some
    assert plane.read_models() is models


def test_world_partners_are_the_radar_partners(monkeypatch: pytest.MonkeyPatch) -> None:
    from eios.cockpit.partner import PartnerWorkstationService

    config = plane.world_config(PartnerWorkstationService())
    assert "PTR-882" in config.partner_ids and "PTR-401" in config.partner_ids
