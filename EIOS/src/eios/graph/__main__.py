"""`python -m eios.graph load --project P` and `python -m eios.graph parity --project P --reservation R`.

`parity` runs every named query on BigQuery Graph and on the local double over the same world and compares the rows,
then checks the shared-exit query against the geo engine's own flags; it prints timings and slot use `[MEASURED]`.
"""

from __future__ import annotations

import argparse
import logging
import statistics
from typing import Any

from eios.dataplane.aml_geo_sessions import HUB_DEGREE, MIN_EXIT_SESSIONS, MIN_SHARED_FOREIGN
from eios.graph.load import load_graph
from eios.graph.store import BigQueryGraphStore, GraphStore, LocalGraphStore

EXIT_PARAMS = {
    "hub_degree": HUB_DEGREE,
    "min_shared": MIN_SHARED_FOREIGN,
    "min_sessions": MIN_EXIT_SESSIONS,
}
# Every country the two list changes name (FATF June 2026, EU January 2026): the geo agent's list-change question.
LIST_CHANGE_COUNTRIES = (
    "BA",
    "BF",
    "BO",
    "DZ",
    "IQ",
    "ML",
    "MZ",
    "NA",
    "NG",
    "RU",
    "TZ",
    "VG",
    "ZA",
)


def _served() -> tuple[Any, Any]:
    from eios.dataplane.geo_plane import geo_snapshot, graph_tables

    snap = geo_snapshot()
    if snap is None:
        raise SystemExit("no engine data plane: set EIOS_DATA_PLANE=engine")
    return snap, graph_tables()


def _key(rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return sorted(tuple(r.values()) for r in rows)


def parity(remote: GraphStore, local: GraphStore, snap: Any, accounts: list[str]) -> int:
    failures = 0
    timings: list[float] = []
    exits = remote.run("shared_exits", EXIT_PARAMS)
    same = _key(exits.rows) == _key(local.run("shared_exits", EXIT_PARAMS).rows)
    engine = set(snap.clients.loc[snap.clients["exit_flag"], "client_id"])
    graph = {r["account_id"] for r in exits.rows}
    print(
        f"shared_exits: {len(exits.rows)} rows, bigquery == local {same}, graph accounts == engine flags {graph == engine} "
        f"({len(graph)} vs {len(engine)}), {exits.seconds}s, slot ms {exits.slot_ms} [MEASURED]"
    )
    failures += (not same) + (graph != engine)
    timings.append(exits.seconds)
    checks: list[tuple[str, dict[str, Any]]] = [
        *(("account_neighbourhood", {"account": a}) for a in accounts),
        *(("exit_ring", {"gateway": g}) for g in sorted({r["gateway_id"] for r in exits.rows})),
        ("country_links", {"countries": list(LIST_CHANGE_COUNTRIES)}),
    ]
    for name, params in checks:
        r = remote.run(name, params)
        ok = _key(r.rows) == _key(local.run(name, params).rows)
        failures += not ok
        timings.append(r.seconds)
        print(
            f"{name} {params}: {len(r.rows)} rows, bigquery == local {ok}, {r.seconds}s, slot ms {r.slot_ms}"
        )
    print(
        f"bigquery graph latency median {statistics.median(timings):.2f}s, max {max(timings):.2f}s over {len(timings)} queries [MEASURED]"
    )
    return failures


def main() -> int:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(prog="python -m eios.graph")
    sub = parser.add_subparsers(dest="cmd", required=True)
    load = sub.add_parser("load")
    load.add_argument("--project", required=True)
    par = sub.add_parser("parity")
    par.add_argument("--project", required=True)
    par.add_argument(
        "--reservation", required=True, help="projects/<p>/locations/<loc>/reservations/<name>"
    )
    par.add_argument("--accounts", nargs="*", default=["CR84920", "CR73491", "CR10005"])
    args = parser.parse_args()
    snap, tables = _served()
    if args.cmd == "load":
        print(load_graph(tables, args.project))
        return 0
    remote = BigQueryGraphStore(args.project, args.reservation, tables.fingerprint)
    return 1 if parity(remote, LocalGraphStore(tables), snap, args.accounts) else 0


if __name__ == "__main__":
    raise SystemExit(main())
