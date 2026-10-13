"""Automated Offline SCM DAG Edge-Weight Recalibration Engine (Principle VII)."""

from __future__ import annotations

import uuid
from collections import defaultdict, deque
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import numpy as np

from eios.flywheel.models import SCMRecalibrationCheckpoint


def parse_edge_key(edge_key: str) -> tuple[str, str]:
    """Parses 'source->target' key into (source, target) tuple."""
    if "->" not in edge_key:
        raise ValueError(f"Invalid edge key '{edge_key}'. Expected 'source->target' format.")
    parts = edge_key.split("->", 1)
    return parts[0].strip(), parts[1].strip()


def verify_dag_acyclicity(edges: Sequence[tuple[str, str]]) -> bool:
    """Verifies that a directed graph contains no cycles using Kahn's algorithm."""
    nodes: set[str] = set()
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)

    for src, tgt in edges:
        nodes.add(src)
        nodes.add(tgt)
        adj[src].append(tgt)
        in_degree[tgt] += 1
        if src not in in_degree:
            in_degree[src] = in_degree[src]

    # Kahn's algorithm: queue of all nodes with in-degree 0
    queue = deque([n for n in nodes if in_degree[n] == 0])
    visited_count = 0

    while queue:
        u = queue.popleft()
        visited_count += 1
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    return visited_count == len(nodes)


class SCMRecalibrator:
    """Offline batch re-estimation of Structural Causal Model DAG edge weights.

    Enforces Principle VII: Decoupled Pipelines. SCM recalibration executes offline
    in scheduled batch routines and never delays real-time interactive coordinator turns.
    """

    def __init__(
        self,
        initial_weights: dict[str, float] | None = None,
        learning_rate: float = 0.05,
        l2_reg: float = 0.01,
        weight_bounds: tuple[float, float] = (-2.0, 2.0),
    ) -> None:
        self.weights: dict[str, float] = dict(initial_weights) if initial_weights else {}
        self.learning_rate = learning_rate
        self.l2_reg = l2_reg
        self.weight_bounds = weight_bounds

    def validate_acyclicity(self, edge_keys: Sequence[str]) -> bool:
        """Ensures that the current edge set forms an acyclic directed graph."""
        parsed_edges = [parse_edge_key(k) for k in edge_keys]
        if not verify_dag_acyclicity(parsed_edges):
            raise ValueError(f"Directed cycle detected in DAG with edges: {edge_keys}")
        return True

    def recalibrate_edges(
        self,
        observations: list[dict[str, Any]],
        version: str = "v1.0.0",
        provenance_seed: str = "default_seed",
    ) -> SCMRecalibrationCheckpoint:
        """Re-estimates edge weights via regularized residual gradient updates.

        Each observation should contain:
        - 'edge': str ('source->target')
        - 'source_val': float
        - 'residual': float (actual - predicted)
        """
        # Group observations by edge
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for obs in observations:
            grouped[obs["edge"]].append(obs)

        # Merge with existing weights
        all_edge_keys = list(set(list(self.weights.keys()) + list(grouped.keys())))
        self.validate_acyclicity(all_edge_keys)

        updated_weights = dict(self.weights)
        baseline_errors: list[float] = []
        recalibrated_errors: list[float] = []

        for edge_key, obs_list in grouped.items():
            curr_weight = self.weights.get(edge_key, 0.0)
            residuals = np.array([o["residual"] for o in obs_list], dtype=np.float64)
            source_vals = np.array([o.get("source_val", 1.0) for o in obs_list], dtype=np.float64)

            baseline_errors.extend(np.abs(residuals).tolist())

            # Regularized gradient: dL/dw = - (1/N) * sum(residual * source_val) + lambda * w
            gradient = float(np.mean(residuals * source_vals))
            delta = self.learning_rate * gradient - self.l2_reg * curr_weight
            new_weight = float(
                np.clip(
                    curr_weight + delta,
                    self.weight_bounds[0],
                    self.weight_bounds[1],
                )
            )
            updated_weights[edge_key] = round(new_weight, 4)

            # Expected error after weight shift
            new_residuals = residuals - (new_weight - curr_weight) * source_vals
            recalibrated_errors.extend(np.abs(new_residuals).tolist())

        baseline_mae = float(np.mean(baseline_errors)) if baseline_errors else 0.0
        recalibrated_mae = float(np.mean(recalibrated_errors)) if recalibrated_errors else 0.0

        self.weights = updated_weights

        return SCMRecalibrationCheckpoint(
            checkpoint_id=str(uuid.uuid4()),
            version=version,
            timestamp=datetime.now(UTC),
            edge_weights=updated_weights,
            baseline_residuals_mae=round(baseline_mae, 4),
            recalibrated_residuals_mae=round(recalibrated_mae, 4),
            is_acyclic=True,
            provenance_seed=provenance_seed,
        )
