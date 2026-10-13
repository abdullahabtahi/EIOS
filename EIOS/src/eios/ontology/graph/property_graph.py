"""In-memory NetworkX Property Graph with Hub Suppression (ADR-004, ADR-008, US3)."""

from collections import deque
from datetime import UTC, datetime
from typing import Any

import networkx as nx

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.graph.hub_suppression import GraphHubSuppressionFilter


class InMemPropertyGraph:
    """High-performance in-memory property graph backed by NetworkX."""

    def __init__(self, hub_threshold: int = 5) -> None:
        self.graph = nx.Graph()
        self.hub_filter = GraphHubSuppressionFilter(degree_threshold=hub_threshold)
        self._last_sync_ts = None

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()

    def has_node(self, node_id: str) -> bool:
        return self.graph.has_node(node_id)

    def get_node_data(self, node_id: str) -> dict[str, Any]:
        return dict(self.graph.nodes.get(node_id, {}))

    def rehydrate_from_hot_state(self, hot_state: HotStateEngine) -> None:
        """Force full rehydration from hot-state tables in DuckDB."""
        self._last_sync_ts = None
        self.sync_from_hot_state(hot_state)

    def sync_from_hot_state(self, hot_state: HotStateEngine) -> None:
        """Incrementally sync nodes and edges from hot-state tables in DuckDB."""
        cursor = hot_state.get_cursor()
        current_sync_ts = datetime.now(UTC)

        if self._last_sync_ts is None:
            time_filter_dev = ""
            time_filter_partner = ""
            params = []
            self.graph.clear()
        else:
            time_filter_dev = "WHERE last_seen > ?"
            time_filter_partner = "WHERE since > ?"
            params = [self._last_sync_ts]

        try:
            # 1. Device network graph edges
            dev_query = f"""
                SELECT source_id, target_id, edge_type, session_count
                FROM device_network_graph
                {time_filter_dev}
            """  # noqa: S608
            dev_edges = cursor.execute(dev_query, params).fetchall()

            # 2. Partner referral tree edges
            partner_query = f"""
                SELECT parent_id, child_id, 'REFERRED_BY' as edge_type, 1 as session_count
                FROM partner_referral_tree
                {time_filter_partner}
            """  # noqa: S608
            partner_edges = cursor.execute(partner_query, params).fetchall()
        finally:
            cursor.close()

        all_edges = dev_edges + partner_edges
        edge_tuples = []
        new_nodes = set()
        for src, tgt, edge_type, sessions in all_edges:
            edge_tuples.append(
                (src, tgt, {"edge_type": edge_type, "weight": float(sessions or 1.0)})
            )
            new_nodes.add(src)
            new_nodes.add(tgt)

        self.graph.add_edges_from(edge_tuples)

        # Compute degrees and evaluate hub suppression tags
        nodes_to_update = new_nodes if self._last_sync_ts else self.graph.nodes
        for node_id in nodes_to_update:
            degree = self.graph.degree[node_id]
            node_type = (
                "Device"
                if str(node_id).startswith("DEV-")
                else ("IPAddress" if str(node_id).startswith("IP-") else "ClientAccount")
            )
            eval_res = self.hub_filter.evaluate_node(node_id, node_type, degree)
            self.graph.nodes[node_id].update(eval_res)

        self._last_sync_ts = current_sync_ts

    def get_ego_graph(
        self,
        seed_id: str,
        hops: int = 2,
        suppress_hubs: bool = True,
    ) -> dict[str, Any]:
        """Extract multi-hop ego-graph around seed_id with optional Hub Suppression."""
        if not self.graph.has_node(seed_id):
            return {"nodes": [], "edges": [], "hub_flags": {}}

        visited_nodes: set[str] = {seed_id}
        discovered_edges: list[dict[str, Any]] = []
        hub_flags: dict[str, bool] = {}

        # BFS with depth tracking: (current_node, current_hop)
        queue: deque[tuple[str, int]] = deque([(seed_id, 0)])

        while queue:
            curr_node, curr_hop = queue.popleft()
            curr_data = self.graph.nodes.get(curr_node, {})
            is_hub = curr_data.get("is_shared_context", False)
            hub_flags[curr_node] = is_hub

            if curr_hop >= hops:
                continue

            for neighbor in self.graph.neighbors(curr_node):
                edge_data = self.graph.get_edge_data(curr_node, neighbor)
                edge_entry = {
                    "source": curr_node,
                    "target": neighbor,
                    "edge_type": edge_data.get("edge_type", "LINK"),
                    "weight": edge_data.get("weight", 1.0),
                }

                # If hub suppression is enabled and current node is a hub,
                # do not expand through it to other nodes!
                if suppress_hubs and is_hub and curr_node != seed_id:
                    continue

                if edge_entry not in discovered_edges:
                    discovered_edges.append(edge_entry)

                if neighbor not in visited_nodes:
                    # If neighbor is a hub and suppress_hubs is True, visit but do not expand
                    visited_nodes.add(neighbor)
                    queue.append((neighbor, curr_hop + 1))

        return {
            "nodes": list(visited_nodes),
            "edges": discovered_edges,
            "hub_flags": hub_flags,
        }

    def detect_communities(self, suppress_hubs: bool = True) -> list[set[str]]:
        """Identify connected components / cliques with optional hub masking."""
        if not suppress_hubs:
            return [set(c) for c in nx.connected_components(self.graph)]

        # Mask edges incident to hub nodes for clustering
        masked_graph = self.graph.copy()
        for node_id, data in self.graph.nodes(data=True):
            if data.get("is_shared_context", False):
                edges_to_remove = list(masked_graph.edges(node_id))
                masked_graph.remove_edges_from(edges_to_remove)

        return [set(c) for c in nx.connected_components(masked_graph) if len(c) > 1]
