"""Parametric shock propagation across structural causal DAG edges (US4)."""

from typing import Any


def scenario_propagate(
    shock_spec: dict[str, float],
    causal_edges: list[dict[str, Any]],
) -> dict[str, float]:
    """Propagate parametric shock across a causal DAG."""
    deltas = dict(shock_spec)

    # Propagate in topological order of edges
    for edge in causal_edges:
        src = edge["from"]
        tgt = edge["to"]
        weight = float(edge.get("weight", 1.0))

        if src in deltas:
            effect = deltas[src] * weight
            deltas[tgt] = round(deltas.get(tgt, 0.0) + effect, 4)

    return deltas
