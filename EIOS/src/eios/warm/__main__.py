"""Load the AML world's history into the warm tier: python -m eios.warm load --backend bigquery --project <id>.

Runs the same world the cockpit serves through the real ingestion pipeline and appends it to the warehouse. Re-running
is safe: the batch id comes from the world and the window, and BigQuery refuses a second load job with the same id.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from eios.dataplane.plane import engine_service, read_models
from eios.warm.loader import load_transactions_history
from eios.warm.sink import BigQueryWarmSink, LocalWarmSink, WarmSink


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m eios.warm")
    ap.add_argument("command", choices=["load"])
    ap.add_argument("--backend", choices=["bigquery", "local"], default="bigquery")
    ap.add_argument("--project", help="the project that owns the warm datasets (bigquery)")
    ap.add_argument("--location", default="us-central1")
    ap.add_argument(
        "--hours",
        type=int,
        default=None,
        help="how far back to load; default is the world's whole span",
    )
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if args.backend == "bigquery" and not args.project:
        print("--project is required for the bigquery backend", file=sys.stderr)
        return 2
    read_models()  # builds the engines, so the world is the one the cockpit serves
    service = engine_service()
    if service is None:
        print(
            "the engine data plane is off (EIOS_DATA_PLANE=fixture): there is no world to load",
            file=sys.stderr,
        )
        return 2
    sink: WarmSink = (
        BigQueryWarmSink(args.project, location=args.location)
        if args.backend == "bigquery"
        else LocalWarmSink()
    )
    world = service.snapshot.world
    summary = load_transactions_history(world, None, sink, hours=args.hours)
    print(
        f"{args.backend}: batch {summary.batch_id}: {summary.offered} offered, {summary.loaded} loaded, "
        f"{summary.quarantined} quarantined ({summary.window_start:%Y-%m-%d} to {summary.window_end:%Y-%m-%d})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
