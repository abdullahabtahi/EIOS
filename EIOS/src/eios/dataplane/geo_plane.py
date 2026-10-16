"""The process-wide geo plane: the geo engine over the AML world the cockpit serves, tiered by the reference layer.

Built lazily on first use, not at start-up, because the tiers come from the warehouse and a slow or missing warehouse
must not hold the other planes back. Without tiers the corridor lens is not measured (reported as None) and the IP lens
still runs. Run `python -m eios.dataplane.geo_plane` to print the measured quality.
"""

from __future__ import annotations

import functools
import logging
import os
import threading
import time
from typing import Any

from eios.dataplane.aml_geo import GeoQuality, GeoSnapshot, run_geo_engine
from eios.dataplane.aml_geo_sessions import LngLat, positions_from
from eios.dataplane.plane import engine_service
from eios.graph.store import BigQueryGraphStore, GraphStore, LocalGraphStore
from eios.graph.tables import GraphTables, build_tables
from eios.reference.reader import ReferenceReader, ReferenceUnavailable, reader_from_env
from eios.reference.tiers import jurisdiction_tiers

logger = logging.getLogger("eios.dataplane.geo")
_lock = threading.Lock()
_snapshot: GeoSnapshot | None = None
_names: dict[str, str] = {}
_graph: GraphTables | None = None
_store: GraphStore | None = None


@functools.cache
def _reader() -> ReferenceReader | None:
    """One reader per process, so the engine build and the geo tools share its cached snapshot of the warehouse."""
    return reader_from_env()


def reference_world() -> dict[str, Any] | None:
    """The reference layer as the warehouse holds it, or None when it is not configured or cannot be read."""
    reader = _reader()
    if reader is None:
        return None
    try:
        return reader.world()
    except Exception:  # a warehouse failure: the caller falls back to the curated lists and says so
        logger.warning("geo plane: reference layer unreadable", exc_info=True)
        return None


def _reference() -> tuple[dict[str, str], dict[str, LngLat]]:
    """Jurisdiction tiers and country centroids; both empty (not invented) when the reference layer is missing."""
    reader = _reader()
    if reader is None:
        logger.warning(
            "geo plane: no reference layer configured; corridor and travel lenses will not be measured"
        )
        return {}, {}
    try:
        world = reader.world()
        _names.update({c["iso2"]: c["name"] for c in world.get("countries", [])})
        return jurisdiction_tiers(world), positions_from(world)
    except (
        ReferenceUnavailable,
        Exception,
    ):  # a warehouse failure leaves the tiers unknown, never invented
        logger.warning(
            "geo plane: reference layer unavailable; corridor and travel lenses will not be measured",
            exc_info=True,
        )
        return {}, {}


def describe(q: GeoQuality) -> str:
    def pct(x: float | None) -> str:
        return "not measured" if x is None else f"{x:.2f}"

    return (
        f"mismatch flagged {q.mismatch_flagged} (assessable {q.mismatch_assessable} of {q.clients}), precision "
        f"{pct(q.mismatch_precision)}, recall {pct(q.mismatch_recall_assessable)} of assessable and "
        f"{pct(q.mismatch_recall_malicious)} of malicious rings; corridor flagged {q.corridor_flagged}, precision "
        f"{pct(q.corridor_precision)}, recall {pct(q.corridor_recall_assessable)} of assessable, planted corridors "
        f"elevated {pct(q.planted_corridors_elevated)}; top-{q.top_k} precision {q.precision_at_k:.2f} against base rate "
        f"{q.base_rate:.3f}, lift {q.lift_at_k:.1f}x [MEASURED]"
        + (_describe_sessions(q) if q.sessions else "")
    )


def _describe_sessions(q: GeoQuality) -> str:
    s = q.sessions
    if s is None:
        return ""

    def pct(x: float | None) -> str:
        return "not measured" if x is None else f"{x:.2f}"

    return (
        f"; shared exit flagged {s.exit_flagged}, precision {pct(s.exit_precision)}, recall {pct(s.exit_recall)} of "
        f"{s.ring_members} ring members; impossible travel flagged {s.jump_flagged}, precision {pct(s.jump_precision)}, "
        f"recall {pct(s.jump_recall)} (without hub suppression {s.jump_flagged_naive} flagged, precision "
        f"{pct(s.jump_precision_naive)}, benign {s.benign_flagged_by_jumps_naive} against {s.benign_flagged_by_jumps}); "
        f"ring members the per-client lens cannot judge {s.rings_not_assessable_per_client}, recovered by the shared "
        f"exit {s.recovered_by_exit} [MEASURED]"
    )


def geo_snapshot() -> GeoSnapshot | None:
    """The geo engine's snapshot, or None on the fixture plane (there is no world to read)."""
    global _snapshot
    service = engine_service()
    if service is None:
        return None
    with _lock:
        if _snapshot is None:
            started = time.perf_counter()
            tiers, positions = _reference()
            _snapshot = run_geo_engine(service.snapshot.world, tiers, positions)
            if _snapshot.quality:
                logger.info(
                    "geo engine built in %.1fs: %s",
                    time.perf_counter() - started,
                    describe(_snapshot.quality),
                )
        return _snapshot


def graph_tables() -> GraphTables | None:
    """The served world as graph tables (built once, from the frames, with the same tiers the engine used)."""
    global _graph
    snap = geo_snapshot()
    if snap is None or snap.world.geo_sessions is None:
        return None
    with _lock:
        if _graph is None:
            _graph = build_tables(snap.world, snap.tiers, _names)
        return _graph


def graph_store() -> GraphStore | None:
    """BigQuery Graph when `EIOS_GRAPH_BACKEND=bigquery` (with `EIOS_GRAPH_PROJECT` and `EIOS_GRAPH_RESERVATION`),
    otherwise the local double over the same tables. None on the fixture plane."""
    global _store
    tables = graph_tables()
    if tables is None:
        return None
    with _lock:
        if _store is None:
            project, reservation = (
                os.environ.get("EIOS_GRAPH_PROJECT"),
                os.environ.get("EIOS_GRAPH_RESERVATION"),
            )
            if os.environ.get("EIOS_GRAPH_BACKEND") == "bigquery" and project and reservation:
                _store = BigQueryGraphStore(project, reservation, tables.fingerprint)
            else:
                _store = LocalGraphStore(tables)
        return _store


def reset_for_testing() -> None:
    global _snapshot, _graph, _store
    with _lock:
        _snapshot = None
        _graph = None
        _store = None
    _reader.cache_clear()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    snap = geo_snapshot()
    if snap is None or snap.quality is None:
        print("no geo plane: the engine data plane is off or the world carries no geo truth")
        return 2
    print(describe(snap.quality))
    print(f"tiers known: {len(snap.tiers)} jurisdictions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
