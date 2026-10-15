"""Measure where a copilot turn's time goes, on the real runtime, the way an operator meets it.

Usage (live: it calls the model and the session store, so it spends a little; run it only when measuring):
    PYTHONPATH=src:. uv run python -m tools.assistant_latency_probe --runs 3

Each run is a new operator thread (a fresh session) asking the scenario's questions in order, so the first turn pays
for creating the session and later turns for reading it, as in the cockpit. Every turn prints its wall time and the
runtime's own breakdown (model, tools, session, screening, other); the summary gives the median per turn position.
The environment is read as the gateway reads it (GOOGLE_CLOUD_PROJECT, EIOS_PERSISTENCE, the Model Armor templates).
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import uuid
from collections.abc import Sequence
from typing import Any

SCENARIOS: dict[str, tuple[str, str | None, tuple[str, ...]]] = {
    # role, entity on screen, questions in order
    "partner": (
        "partner_manager",
        "PTR-9699",
        ("Why is PTR-9699 at risk?", "Why is this partner high value?"),
    ),
    "aml": (
        "aml_investigator",
        "CR84920",
        ("Summarise this case.", "What does the shared IP evidence say?"),
    ),
}
STAGES = ("model", "tools", "session", "screening", "other")


async def _run(scenario: str, runs: int) -> list[list[dict[str, Any]]]:
    from eios.cockpit.assistant_gateway import get_runtime, warm_up
    from eios.ontology.omcp.port.principal import principal_for

    role, entity, questions = SCENARIOS[scenario]
    await (
        warm_up()
    )  # as the API does at start-up, so the probe does not measure first-connection costs
    runtime = get_runtime()
    results: list[list[dict[str, Any]]] = []
    for run in range(runs):
        principal = principal_for(f"latency-probe-{uuid.uuid4().hex[:8]}", role)
        turns: list[dict[str, Any]] = []
        for position, question in enumerate(questions, start=1):
            out = await runtime.run_turn(principal=principal, question=question, entity_id=entity)
            row = {
                "wall": round(out.latency_ms),
                "status": out.status,
                "calls": out.model_calls,
                **out.timing,
            }
            turns.append(row)
            stages = " ".join(f"{k}={round(row.get(k, 0))}" for k in STAGES)
            print(
                f"run {run + 1} turn {position}: wall={row['wall']} ms ({row['status']}, {row['calls']} model calls) {stages}"
            )
        results.append(turns)
    await runtime.flush()
    return results


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.assistant_latency_probe")
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), default="partner")
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args(argv)
    results = asyncio.run(_run(args.scenario, args.runs))
    for position in range(len(results[0])):
        rows = [run[position] for run in results]
        medians = {
            k: round(statistics.median(r.get(k, 0) for r in rows)) for k in ("wall", *STAGES)
        }
        print(
            f"median turn {position + 1} over {len(rows)} runs: "
            + " ".join(f"{k}={v}" for k, v in medians.items())
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
