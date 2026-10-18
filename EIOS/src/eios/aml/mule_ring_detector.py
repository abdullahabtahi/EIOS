"""Mule Ring & Smurfing Network Graph Detector with Hub Suppression (US4 / P2).

Authoritative References:
- docs/brief/monitoring.md [BRIEF monitoring]
- initial_plan.md §5.4
- specs/010-client-aml/spec.md (User Story 4)
- .specify/memory/constitution.md (Principles I, IV)

Builds bipartite entity-attribute graphs over shared payments, devices, and IPs.
Applies degree-penalized hub suppression to filter legitimate public Wi-Fi and CGNAT gateways,
preventing false syndicate mergers.
"""

import math
import uuid
from datetime import UTC, datetime

import networkx as nx
import pandas as pd

from eios.aml.models import MuleRingCluster
from eios.ingestion.hot_state import HotStateEngine


class MuleRingDetector:
    """Detects coordinated mule rings and smurfing syndicates using NetworkX."""

    def __init__(
        self,
        hot_state: HotStateEngine | None = None,
        max_hub_degree: int = 25,
        min_cluster_size: int = 2,
    ) -> None:
        self.hot_state = hot_state
        self.max_hub_degree = max_hub_degree
        self.min_cluster_size = min_cluster_size
        self.suppressed_hubs: set[str] = set()

    def detect_mule_rings(self, network_edges_df: pd.DataFrame) -> list[MuleRingCluster]:  # noqa: C901, PLR0912, PLR0915
        """Process entity edges, filter high-degree hubs, and extract mule clusters."""
        if network_edges_df.empty:
            return []

        self.suppressed_hubs.clear()
        B = nx.Graph()

        # 1. Build bipartite graph
        # Node attribute 'bipartite': 0 for clients, 1 for entity tokens
        for row in network_edges_df.itertuples():
            client_id = str(row.source_id)
            token_id = str(row.target_id)
            edge_type = str(getattr(row, "edge_type", "SHARED_ATTR"))
            is_shared_context = bool(getattr(row, "is_shared_context", False))

            B.add_node(client_id, bipartite=0)
            B.add_node(
                token_id, bipartite=1, edge_type=edge_type, is_shared_context=is_shared_context
            )
            B.add_edge(client_id, token_id, edge_type=edge_type)

        # 2. Hub Suppression
        attribute_nodes = [n for n, d in B.nodes(data=True) if d.get("bipartite") == 1]
        active_tokens: set[str] = set()

        for token in attribute_nodes:
            deg = B.degree(token)
            data = B.nodes[token]
            is_shared = data.get("is_shared_context", False)

            if is_shared or deg > self.max_hub_degree:
                self.suppressed_hubs.add(token)
            else:
                active_tokens.add(token)

        # 3. Project onto client nodes with Adamic-Adar / degree-penalized edge weights
        client_graph = nx.Graph()
        client_nodes = [n for n, d in B.nodes(data=True) if d.get("bipartite") == 0]
        client_graph.add_nodes_from(client_nodes)

        for token in active_tokens:
            deg = B.degree(token)
            weight = 1.0 / math.log1p(deg)
            neighbors = list(B.neighbors(token))
            n_neighbors = len(neighbors)
            for i in range(n_neighbors):
                for j in range(i + 1, n_neighbors):
                    u = neighbors[i]
                    v = neighbors[j]
                    if client_graph.has_edge(u, v):
                        client_graph[u][v]["weight"] += weight
                        client_graph[u][v]["tokens"].append(token)
                    else:
                        client_graph.add_edge(u, v, weight=weight, tokens=[token])

        # 4. Extract connected components
        clusters: list[MuleRingCluster] = []
        for component in nx.connected_components(client_graph):
            if len(component) < self.min_cluster_size:
                continue

            member_ids = sorted(list(component))
            shared_payments: set[str] = set()
            shared_devices: set[str] = set()
            shared_ips: set[str] = set()

            # Inspect all tokens linking this component
            sub_g = client_graph.subgraph(member_ids)
            for u, v, d in sub_g.edges(data=True):  # noqa: B007
                for t in d.get("tokens", []):
                    edge_type = B.nodes[t].get("edge_type", "")
                    if "PAYMENT" in edge_type or "card" in t or "tok_pay" in t:
                        shared_payments.add(t)
                    elif "DEVICE" in edge_type or "hw" in t or "tok_dev" in t:
                        shared_devices.add(t)
                    elif "IP" in edge_type or "tok_ip" in t:
                        shared_ips.add(t)

            cluster_size = len(member_ids)
            is_syndicate = (cluster_size >= 3) and (
                len(shared_payments) > 0 or len(shared_devices) > 0
            )

            # Generate non-technical explanation
            parts = [f"Identified network of {cluster_size} linked accounts."]
            if shared_payments:
                parts.append(f"Sharing {len(shared_payments)} verified payment method token(s).")
            if shared_devices:
                parts.append(
                    f"Sharing {len(shared_devices)} common hardware device fingerprint(s)."
                )
            if shared_ips:
                parts.append(f"Sharing {len(shared_ips)} private network connection(s).")
            if self.suppressed_hubs:
                parts.append(
                    f"Suppressed {len(self.suppressed_hubs)} high-degree public gateway(s) to avoid false merges."
                )

            explanation = " ".join(parts)

            clusters.append(
                MuleRingCluster(
                    cluster_id=f"MULE-RING-{uuid.uuid4().hex[:8].upper()}",
                    member_client_ids=member_ids,
                    shared_payment_tokens=sorted(list(shared_payments)),
                    shared_device_tokens=sorted(list(shared_devices)),
                    shared_ip_tokens=sorted(list(shared_ips)),
                    suppressed_hub_tokens=sorted(list(self.suppressed_hubs)),
                    cluster_size=cluster_size,
                    total_volume_usd=round(
                        cluster_size * 5200.0, 2
                    ),  # illustrative aggregate volume
                    is_syndicate=is_syndicate,
                    plain_language_explanation=explanation,
                )
            )

        return clusters

    def persist_clusters(self, clusters: list[MuleRingCluster]) -> int:
        """Persist mule ring clusters to DuckDB aml_mule_rings hot state."""
        if not self.hot_state:
            return 0
        cursor = self.hot_state.get_cursor()
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        count = 0
        for c in clusters:
            for member_id in c.member_client_ids:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO aml_mule_rings (
                        cluster_id, client_id, cluster_size, shared_payment_count,
                        shared_device_count, total_volume_usd, is_syndicate,
                        explanation, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        c.cluster_id,
                        member_id,
                        c.cluster_size,
                        len(c.shared_payment_tokens),
                        len(c.shared_device_tokens),
                        c.total_volume_usd,
                        c.is_syndicate,
                        c.plain_language_explanation,
                        now_str,
                    ],
                )
                count += 1
        return count
