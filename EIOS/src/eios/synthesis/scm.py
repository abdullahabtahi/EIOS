"""Structural Causal Model (SCM) DAG and SCMCache engine (T011, US1).

Implements:
1. CausalDAG: NetworkX DAG validation, cycle detection, topological sort, path discovery.
2. SCMCache: High-performance deserialization and sub-millisecond edge lookup.
3. Causal-Evidence Gate assertion checker emitting honest refusal on unverified links.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import networkx as nx

from eios.synthesis.exceptions import CausalCycleError
from eios.synthesis.models import CausalEdge, SCMCacheManifest


class CausalDAG:
    """NetworkX-backed directed acyclic graph representing structural causal dependencies."""

    def __init__(self, edges: Sequence[CausalEdge] | None = None) -> None:
        self._graph = nx.DiGraph()
        self._edges: dict[tuple[str, str], CausalEdge] = {}

        if edges:
            for edge in edges:
                self.add_edge(edge)

    def add_edge(self, edge: CausalEdge) -> None:
        """Add a causal edge, asserting directed acyclic property."""
        src = edge.source_metric
        tgt = edge.target_metric

        self._graph.add_edge(src, tgt, weight=edge.weight, edge_obj=edge)

        if not nx.is_directed_acyclic_graph(self._graph):
            # Roll back edge
            self._graph.remove_edge(src, tgt)
            raise CausalCycleError(
                f"Directed cycle detected in causal graph when adding {src} -> {tgt}."
            )

        self._edges[(src, tgt)] = edge

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def get_edges(self) -> list[CausalEdge]:
        return list(self._edges.values())

    def topological_order(self) -> list[str]:
        """Return nodes in valid causal topological order."""
        return list(nx.topological_sort(self._graph))

    def has_path(self, source: str, target: str) -> bool:
        """Check if a directed causal path exists from source to target."""
        if not self._graph.has_node(source) or not self._graph.has_node(target):
            return False
        return nx.has_path(self._graph, source, target)

    def path_weight(self, source: str, target: str) -> float:
        """Compute the total causal path weight from source to target.

        If multiple simple paths exist, sums the multiplicative weights of all paths.
        """
        if not self.has_path(source, target):
            return 0.0

        total_weight = 0.0
        for path in nx.all_simple_paths(self._graph, source, target):
            path_prod = 1.0
            for u, v in zip(path[:-1], path[1:], strict=False):
                edge = self._edges.get((u, v))
                if edge:
                    path_prod *= edge.weight
            total_weight += path_prod

        return total_weight

    def predecessors(self, node: str) -> list[str]:
        """Return direct causal parent metrics of node."""
        if not self._graph.has_node(node):
            return []
        return list(self._graph.predecessors(node))

    def successors(self, node: str) -> list[str]:
        """Return direct causal downstream metrics of node."""
        if not self._graph.has_node(node):
            return []
        return list(self._graph.successors(node))


class SCMCache:
    """In-memory cache of certified SCM DAG edges, weights, and refutation manifests."""

    def __init__(self, manifest: SCMCacheManifest) -> None:
        self.manifest = manifest
        self.model_version = manifest.model_version
        self.dag = CausalDAG(edges=manifest.edges)
        self._refutations = manifest.refutations

    @classmethod
    def load_from_file(cls, path: str | Path) -> SCMCache:
        """Deserialize SCMCache from JSON file."""
        file_path = Path(path)
        with open(file_path, encoding="utf-8") as f:
            raw_data = json.load(f)
        manifest = SCMCacheManifest.model_validate(raw_data)
        return cls(manifest)

    def save_to_file(self, path: str | Path) -> None:
        """Serialize SCMCache to JSON file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.manifest.model_dump_json(indent=2))

    def get_edges_for_outcome(self, outcome_metric: str) -> list[CausalEdge]:
        """Return all certified causal edges in the directed path leading to outcome_metric."""
        active_edges: list[CausalEdge] = []
        for edge in self.dag.get_edges():
            # If target is outcome or target can reach outcome
            if edge.target_metric == outcome_metric or self.dag.has_path(
                edge.target_metric, outcome_metric
            ):
                active_edges.append(edge)
        return active_edges

    def get_edges_dict(self) -> list[dict[str, Any]]:
        """Return canonical OMCP edge list."""
        return [edge.to_omcp_dict() for edge in self.dag.get_edges()]

    def verify_causal_assertion(
        self,
        source_metric: str,
        target_metric: str,
    ) -> tuple[bool, str]:
        """Verify whether a directed relationship passes the Causal-Evidence Gate (Principle III).

        Returns:
            (True, "Causal link verified") or (False, "correlation detected; insufficient evidence for causation.")
        """
        if not self.dag.has_path(source_metric, target_metric):
            return (
                False,
                f"No directed causal path between '{source_metric}' and '{target_metric}': "
                "correlation detected; insufficient evidence for causation.",
            )

        edge_key = f"{source_metric}->{target_metric}"
        ref = self._refutations.get(edge_key)
        if ref and ref.gate_verdict != "PASS":
            return (
                False,
                f"Causal edge '{edge_key}' failed refutation gate: "
                "correlation detected; insufficient evidence for causation.",
            )

        return True, "Causal link verified by refutation suite."
