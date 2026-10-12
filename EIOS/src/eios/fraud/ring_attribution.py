"""NetworkX 3-Layer Referral Ring Mapping & Master Partner Attribution (US2 / Module B).

Authoritative References:
- docs/brief/fraud [BRIEF fraud]
- specs/009-partner-fraud/spec.md (US2, FR-004, FR-005, SC-003)
- specs/009-partner-fraud/research.md §2
"""

from collections import deque
import math
import networkx as nx

from eios.fraud.models import ReferralRingNode, RingAttribution


class ReferralRingAttributionEngine:
    """Traverses multi-tier sub-affiliate hierarchies up to 3 layers deep.

    Key Features:
    1. Upstream Master Attribution: Recovers root master partner for any sub-affiliate.
    2. Cycle Detection: Identifies circular referral loops (A -> B -> A) and breaks them safely.
    3. Degree-Penalized Hub Suppression: Dampens risk scores for legitimate high-degree
       broker hubs (e.g. regional introducing brokers with > 50 sub-affiliates).
    4. Exposure Rollup: Aggregates direct client counts, commission volume, and flagged abuse.
    """

    def __init__(self, hub_degree_threshold: int = 50) -> None:
        self.hub_degree_threshold = hub_degree_threshold
        # G_down: edges from parent -> child
        self.g_down = nx.DiGraph()
        # G_up: edges from child -> parent
        self.g_up = nx.DiGraph()
        self.node_attrs: dict[str, dict] = {}

    def build_graph(self, partner_nodes: list[dict]) -> None:
        """Construct directed referral trees from partner network records."""
        self.g_down.clear()
        self.g_up.clear()
        self.node_attrs.clear()

        # Add all nodes first
        for p in partner_nodes:
            pid = p["partner_id"]
            self.node_attrs[pid] = {
                "tier_level": p.get("tier_level", 1),
                "direct_referred_clients": p.get("direct_referred_clients", 0),
                "direct_commission_usd": float(p.get("direct_commission_usd", 0.0)),
                "sub_affiliate_count": p.get("sub_affiliate_count", 0),
                "is_root_master": p.get("is_root_master", False),
                "abuse_ratio": float(p.get("abuse_ratio", 0.70)),
            }
            self.g_down.add_node(pid, **self.node_attrs[pid])
            self.g_up.add_node(pid, **self.node_attrs[pid])

        # Add directed edges and check cycles
        for p in partner_nodes:
            child_id = p["partner_id"]
            parent_id = p.get("parent_partner_id")
            if parent_id and parent_id in self.node_attrs:
                # Avoid self-loops
                if child_id == parent_id:
                    continue

                # Check if adding edge parent_id -> child_id creates a cycle
                if self.g_down.has_node(parent_id) and self.g_down.has_node(child_id):
                    if nx.has_path(self.g_down, child_id, parent_id):
                        # Cycle detected: break loop
                        continue

                self.g_down.add_edge(parent_id, child_id)
                self.g_up.add_edge(child_id, parent_id)

    def find_root_master(self, partner_id: str) -> str:
        """Traverse upstream via g_up to locate top-level root master partner."""
        if partner_id not in self.g_up:
            return partner_id

        current = partner_id
        visited = set()

        while current not in visited:
            visited.add(current)
            parents = list(self.g_up.successors(current))
            if not parents:
                break
            # Pick first parent (or explicit tier 1)
            current = parents[0]

        return current

    def attribute_partner_ring(
        self,
        partner_id: str,
        flagged_abuse_commissions: dict[str, float] | None = None,
    ) -> RingAttribution:
        """Map full referral tree for the partner and attribute back to Master Partner."""
        flagged_abuse_commissions = flagged_abuse_commissions or {}
        master_id = self.find_root_master(partner_id)

        # BFS from master down up to 3 layers
        ring_nodes_map: dict[str, ReferralRingNode] = {}
        queue: deque[tuple[str, str | None, int]] = deque([(master_id, None, 1)])
        visited = set()

        while queue:
            curr_id, parent_id, depth = queue.popleft()
            if curr_id in visited or depth > 3:
                continue
            visited.add(curr_id)

            attrs = self.node_attrs.get(curr_id, {})
            direct_clients = attrs.get("direct_referred_clients", 0)
            direct_comm = attrs.get("direct_commission_usd", 0.0)
            graph_out_degree = self.g_down.out_degree(curr_id) if self.g_down.has_node(curr_id) else 0
            sub_count = max(graph_out_degree, attrs.get("sub_affiliate_count", 0))

            ring_nodes_map[curr_id] = ReferralRingNode(
                partner_id=curr_id,
                parent_partner_id=parent_id,
                tier_level=depth,
                direct_referred_clients=direct_clients,
                direct_commission_usd=round(direct_comm, 2),
                sub_affiliate_count=sub_count,
                is_root_master=(curr_id == master_id),
            )

            # Traverse children
            if self.g_down.has_node(curr_id) and depth < 3:
                for child_id in self.g_down.successors(curr_id):
                    if child_id not in visited:
                        queue.append((child_id, curr_id, depth + 1))

        nodes_list = list(ring_nodes_map.values())
        total_partners = len(nodes_list)
        total_clients = sum(n.direct_referred_clients for n in nodes_list)
        total_comm = sum(n.direct_commission_usd for n in nodes_list)
        max_depth = max((n.tier_level for n in nodes_list), default=1)

        # Calculate flagged abuse commission
        flagged_comm = 0.0
        for n in nodes_list:
            if n.partner_id in flagged_abuse_commissions:
                flagged_comm += flagged_abuse_commissions[n.partner_id]
            else:
                # Default estimate based on node's abuse ratio (0.05 baseline for legitimate nodes)
                ratio = self.node_attrs.get(n.partner_id, {}).get("abuse_ratio", 0.05)
                flagged_comm += n.direct_commission_usd * ratio

        # Top violating sub partners
        violating = sorted(
            [n.partner_id for n in nodes_list if not n.is_root_master],
            key=lambda pid: self.node_attrs.get(pid, {}).get("direct_commission_usd", 0.0),
            reverse=True,
        )

        # Ring Risk Score with Degree-Penalized Hub Suppression
        master_degree = ring_nodes_map[master_id].sub_affiliate_count
        hub_penalty = 1.0
        if master_degree > self.hub_degree_threshold:
            # Hub suppression: log penalty for legitimate massive brokers
            hub_penalty = 1.0 / (1.0 + math.log10(master_degree + 1))

        base_risk = min(1.0, (flagged_comm / (total_comm + 1e-6)) * (1.0 + (max_depth - 1) * 0.15))
        ring_risk_score = round(base_risk * hub_penalty, 4)

        return RingAttribution(
            ring_id=f"RING-{master_id}",
            master_partner_id=master_id,
            total_affiliated_partners=total_partners,
            total_referred_clients=total_clients,
            hierarchy_depth=max_depth,
            total_ring_commission_usd=round(total_comm, 2),
            flagged_abuse_commission_usd=round(flagged_comm, 2),
            ring_risk_score=ring_risk_score,
            top_violating_sub_partners=violating[:5],
            nodes=nodes_list,
        )
