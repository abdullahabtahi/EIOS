"""Prepared briefs against fresh turns, over a running gateway (docs/ambient-dossiers.md).

Prepares the top alerts' briefs, then for each alert reads the prepared brief (the "after") and runs the same "brief
me" turn live (the "before", what an operator waited for). Reports time to first brief both ways and whether the
prepared brief's figures match the fresh turn's: the same fact ids, at the same values.

    python -m evals.agent.ambient_eval --base http://localhost:8012 --top 5 --out evals/reports/ambient_eval.json

Spends model calls (top alerts, twice each); run it only when asked.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

QUESTION = "Brief me on this case."
WAIT_S = 240.0


def _call(
    base: str, path: str, *, body: dict[str, Any] | None = None, method: str = "GET"
) -> tuple[int, Any, float]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(  # noqa: S310 (the base is checked to be http(s) in main)
        base + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    ms = (time.perf_counter() - started) * 1000
    return status, (json.loads(raw) if raw else None), ms


def top_entities(base: str, n: int) -> list[str]:
    _, body, _ = _call(base, "/api/cockpit/workstations/aml_investigator")
    return [str(item["entity_id"]) for item in body["triage_queue"]["items"][:n]]


def figures(citations: list[dict[str, Any]]) -> dict[str, float]:
    """Fact id to value, by the value the tool returned: how the model wrote it ("$1,060" or "$1060") is not a difference."""
    return {c["metric_id"]: float(c["raw_value"]) for c in citations}


def compare(cached: dict[str, float], fresh: dict[str, float]) -> dict[str, Any]:
    shared = set(cached) & set(fresh)
    same = [i for i in shared if cached[i] == fresh[i]]
    return {
        "cached_figures": len(cached),
        "fresh_figures": len(fresh),
        "shared": len(shared),
        "same_value": len(same),
        "only_in_cached": sorted(set(cached) - set(fresh)),
        "only_in_fresh": sorted(set(fresh) - set(cached)),
    }


def run(base: str, top: int) -> dict[str, Any]:
    entities = top_entities(base, top)
    started = time.perf_counter()
    status, _, _ = _call(base, f"/api/cockpit/ambient/refresh?n={top}", method="POST")
    if status != 202:
        raise SystemExit(f"refresh was not accepted: HTTP {status}")
    deadline = time.monotonic() + WAIT_S
    pending = set(entities)
    while pending and time.monotonic() < deadline:
        for entity in list(pending):
            if _call(base, f"/api/cockpit/ambient/briefs/{entity}")[0] == 200:
                pending.discard(entity)
        time.sleep(1.0)
    prepare_s = time.perf_counter() - started
    rows = []
    for entity in entities:
        status, brief, read_ms = _call(base, f"/api/cockpit/ambient/briefs/{entity}")
        _, fresh, fresh_ms = _call(
            base,
            "/api/cockpit/copilot/query",
            body={"query": QUESTION, "role": "aml_investigator", "context_entity_id": entity},
            method="POST",
        )
        row: dict[str, Any] = {
            "entity_id": entity,
            "read_ms": round(read_ms, 1),
            "fresh_ms": round(fresh_ms, 1),
        }
        if status == 200 and fresh:
            row["fresh_status"] = fresh.get("assistant_status")
            row.update(
                compare(
                    figures(brief["provenance_citations"]), figures(fresh["provenance_citations"])
                )
            )
        else:
            row["prepared"] = False
        rows.append(row)
    read = [r["read_ms"] for r in rows]
    fresh_t = [r["fresh_ms"] for r in rows]
    judged = [r for r in rows if "shared" in r]
    return {
        "top": top,
        "prepared": len(judged),
        "prepare_seconds": round(prepare_s, 1),
        "read_ms_median": statistics.median(read) if read else None,
        "fresh_ms_median": statistics.median(fresh_t) if fresh_t else None,
        "figures_same_value": sum(r["same_value"] for r in judged),
        "figures_in_both": sum(r["shared"] for r in judged),
        "briefs": rows,
    }


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m evals.agent.ambient_eval")
    ap.add_argument("--base", default="http://localhost:8012")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    if not args.base.startswith(("http://", "https://")):
        ap.error("--base must be an http(s) URL")
    result = run(args.base, args.top)
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
