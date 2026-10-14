"""What one planted typology contributes to the world, and how contributions combine (spec 031 FR-002)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Rows = list[dict[str, Any]]


@dataclass(frozen=True)
class Planted:
    """Rows, graph edges, client-field overrides and truth tags for some planted clients."""

    txns: tuple[dict[str, Any], ...] = ()
    trades: tuple[dict[str, Any], ...] = ()
    edges: tuple[dict[str, Any], ...] = ()
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    tags: dict[str, tuple[str, ...]] = field(default_factory=dict)
    rings: dict[str, tuple[str, ...]] = field(default_factory=dict)


def merge(parts: list[Planted]) -> Planted:
    """One `Planted` holding everything in `parts`; a client's tags and overrides accumulate."""
    tags: dict[str, tuple[str, ...]] = {}
    overrides: dict[str, dict[str, Any]] = {}
    rings: dict[str, tuple[str, ...]] = {}
    for part in parts:
        for cid, found in part.tags.items():
            tags[cid] = (*tags.get(cid, ()), *found)
        for cid, fields in part.overrides.items():
            overrides[cid] = {**overrides.get(cid, {}), **fields}
        rings = {**rings, **part.rings}
    return Planted(
        txns=tuple(r for p in parts for r in p.txns),
        trades=tuple(r for p in parts for r in p.trades),
        edges=tuple(r for p in parts for r in p.edges),
        overrides=overrides,
        tags=tags,
        rings=rings,
    )
