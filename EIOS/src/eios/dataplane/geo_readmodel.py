"""What the geo capabilities read, behind one seam: the geo engine's snapshot, the graph store and the reference lists.

The served plane builds them lazily from the AML world it serves (`geo_plane`), so a screen and an answer read the same
objects. An offline run (the scripted baseline, tests) builds a world itself, tiered from the curated lists in code and
with no country positions: the travel lens then says it cannot judge, it never guesses. Nothing here reads the truth.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from eios.dataplane.aml_geo import GeoSnapshot, run_geo_engine
from eios.dataplane.aml_geo_sessions import LngLat
from eios.foundry.scenarios.aml_config import AmlWorldConfig
from eios.foundry.scenarios.aml_world import AmlWorld, build_aml_world
from eios.graph.store import GraphStore, LocalGraphStore
from eios.graph.tables import build_tables
from eios.ontology.omcp.port.contracts import DataOrigin
from eios.reference.editions import curated_reference
from eios.reference.tiers import jurisdiction_tiers

WAREHOUSE = "reference layer in BigQuery (warm_reference)"
CURATED = "curated FATF, EU and Basel tables in code (no warehouse here)"


class GeoReadModel(Protocol):
    @property
    def origin(self) -> DataOrigin:
        """Where the snapshot's numbers come from: the served engine, or a world a test or offline run built."""
        ...

    def snapshot(self) -> GeoSnapshot | None:
        """The geo engine's snapshot, or None when no world is served here."""
        ...

    def graph(self) -> GraphStore | None:
        """The graph store (BigQuery Graph or its local double), or None when no world is served here."""
        ...

    def reference(self) -> tuple[Mapping[str, Any], str]:
        """The reference countries and which layer they came from."""
        ...


@dataclass(frozen=True)
class PlaneGeo:
    """The served plane: the engine's world, the configured graph store and the warehouse's reference layer."""

    origin: DataOrigin = DataOrigin.ENGINE

    def snapshot(self) -> GeoSnapshot | None:
        from eios.dataplane.geo_plane import geo_snapshot

        return geo_snapshot()

    def graph(self) -> GraphStore | None:
        from eios.dataplane.geo_plane import graph_store

        return graph_store()

    def reference(self) -> tuple[Mapping[str, Any], str]:
        from eios.dataplane.geo_plane import reference_world

        world = reference_world()
        return (world, WAREHOUSE) if world else (curated_reference(), CURATED)


@dataclass(frozen=True)
class StaticGeo:
    """A world built by its caller: the scripted baseline and tests. Its origin is what the caller says it is."""

    snap: GeoSnapshot
    store: GraphStore | None
    origin: DataOrigin = DataOrigin.FIXTURE
    countries: Mapping[str, Any] = field(default_factory=curated_reference)
    layer: str = CURATED

    def snapshot(self) -> GeoSnapshot | None:
        return self.snap

    def graph(self) -> GraphStore | None:
        return self.store

    def reference(self) -> tuple[Mapping[str, Any], str]:
        return self.countries, self.layer


def curated_tiers() -> dict[str, str]:
    """The jurisdiction tiers the curated lists alone give (no offshore counts without the warehouse)."""
    return jurisdiction_tiers(curated_reference())


def offline_geo(
    world: AmlWorld | None = None, positions: Mapping[str, LngLat] | None = None
) -> StaticGeo:
    """A geo plane over a seeded world with the curated tiers and the local graph double."""
    world = world or build_aml_world(AmlWorldConfig())
    tiers = curated_tiers()
    return StaticGeo(
        run_geo_engine(world, tiers, positions), LocalGraphStore(build_tables(world, tiers))
    )
