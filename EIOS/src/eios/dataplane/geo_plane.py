"""The process-wide geo plane: the geo engine over the AML world the cockpit serves, tiered by the reference layer.

Built lazily on first use, not at start-up, because the tiers come from the warehouse and a slow or missing warehouse
must not hold the other planes back. Without tiers the corridor lens is not measured (reported as None) and the IP lens
still runs. Run `python -m eios.dataplane.geo_plane` to print the measured quality.
"""

from __future__ import annotations

import logging
import threading
import time

from eios.dataplane.aml_geo import GeoQuality, GeoSnapshot, run_geo_engine
from eios.dataplane.plane import engine_service
from eios.reference.reader import ReferenceUnavailable, reader_from_env
from eios.reference.tiers import jurisdiction_tiers

logger = logging.getLogger("eios.dataplane.geo")
_lock = threading.Lock()
_snapshot: GeoSnapshot | None = None


def _tiers() -> dict[str, str]:
    reader = reader_from_env()
    if reader is None:
        logger.warning(
            "geo plane: no reference layer configured; corridor lens will not be measured"
        )
        return {}
    try:
        return jurisdiction_tiers(reader.world())
    except (
        ReferenceUnavailable,
        Exception,
    ):  # a warehouse failure leaves the tiers unknown, never invented
        logger.warning(
            "geo plane: reference layer unavailable; corridor lens will not be measured",
            exc_info=True,
        )
        return {}


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
            _snapshot = run_geo_engine(service.snapshot.world, _tiers())
            if _snapshot.quality:
                logger.info(
                    "geo engine built in %.1fs: %s",
                    time.perf_counter() - started,
                    describe(_snapshot.quality),
                )
        return _snapshot


def reset_for_testing() -> None:
    global _snapshot
    with _lock:
        _snapshot = None


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
