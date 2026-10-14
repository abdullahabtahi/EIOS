"""Score a regulatory index against cases with known answers: recall at k, and silence on what it cannot answer.

A hit is a passage from an expected document whose page span overlaps an expected page. The metrics are the share of
answerable questions with a hit in the first k passages, and the share of unanswerable questions that got no passage.
Nothing here calls a model: it measures retrieval alone, so a failure can be placed in the index or the parser and not
in the answer wording.
"""

from __future__ import annotations

import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from eios.common.validation import StrictModel
from eios.knowledge.passage import IndexUnavailable, Passage, RegulationIndex

KS = (1, 3, 5)
_PAGES = re.compile(r"^(\d+)(?:-(\d+))?$")


class Expect(StrictModel):
    document_id: str
    pages: tuple[int, ...] = Field(min_length=1)


class RetrievalCase(StrictModel):
    id: str
    question: str
    jurisdiction: str | None = None
    expect: tuple[Expect, ...] = ()


def load_cases(path: Path) -> tuple[RetrievalCase, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return tuple(RetrievalCase.model_validate(c) for c in raw["cases"])


def page_span(pages: str) -> range:
    """ "41" is page 41, "41-42" pages 41 and 42, "n/a" no page."""
    match = _PAGES.match(pages)
    if match is None:
        return range(0)
    start = int(match[1])
    return range(start, int(match[2] or start) + 1)


def is_hit(passage: Passage, expected: Sequence[Expect]) -> bool:
    span = set(page_span(passage.pages))
    return any(e.document_id == passage.document_id and span & set(e.pages) for e in expected)


def first_hit_rank(passages: Sequence[Passage], expected: Sequence[Expect]) -> int | None:
    """1-based rank of the first passage that is a hit, or None."""
    return next((i for i, p in enumerate(passages, start=1) if is_hit(p, expected)), None)


def evaluate(
    index: RegulationIndex, cases: Sequence[RetrievalCase], limit: int = max(KS)
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        error: str | None = None
        try:
            found = index.search(case.question, case.jurisdiction, limit)
        except (
            IndexUnavailable
        ) as exc:  # an outage is a miss with its reason, not a crash of the whole run
            found, error = [], str(exc) or "unavailable"
        rows.append(
            {
                "id": case.id,
                "answerable": bool(case.expect),
                "rank": first_hit_rank(found, case.expect) if case.expect else None,
                "returned": len(found),
                "latency_s": round(time.perf_counter() - started, 2),
                "error": error,
                "top": [f"{p.document_id} p.{p.pages}" for p in found[:3]],
            }
        )
    answerable = [r for r in rows if r["answerable"]]
    silent = [r for r in rows if not r["answerable"]]
    return {
        "cases": len(rows),
        "answerable": len(answerable),
        "unanswerable": len(silent),
        **{
            f"recall_at_{k}": round(
                sum(1 for r in answerable if r["rank"] and r["rank"] <= k)
                / max(len(answerable), 1),
                3,
            )
            for k in KS
        },
        "errors": sum(1 for r in rows if r["error"]),
        "latency_s_median": round(sorted(r["latency_s"] for r in rows)[len(rows) // 2], 2),
        "latency_s_max": max(r["latency_s"] for r in rows),
        "silence_on_unanswerable": round(
            sum(1 for r in silent if r["returned"] == 0 and not r["error"]) / max(len(silent), 1), 3
        ),
        "rows": rows,
    }
