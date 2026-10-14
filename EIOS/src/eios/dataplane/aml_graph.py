"""The investigator's network view of one account, from the world's own tokens (spec 031 FR-007).

Shared infrastructure above the RL-4 degree is drawn as one suppressed node with its true degree, never expanded;
a mule ring is drawn as a collapsed cluster hub plus its closest members, with the measured timing gap.
"""

from __future__ import annotations

import pandas as pd

from eios.cockpit.aml import KineticEdge, KineticNetworkGraph, KineticNode, KineticNodeType
from eios.dataplane.aml_engine import AmlSnapshot
from eios.foundry.scenarios.aml_config import PAYMENT_AGENT_HUB
from eios.foundry.scenarios.aml_rows import DEVICE, IP_ADDRESS, PAYMENT

_MAX_MEMBERS_SHOWN = 8
_NODE_TYPE = {
    PAYMENT: KineticNodeType.PAYMENT_AGENT,
    DEVICE: KineticNodeType.DEVICE_FINGERPRINT,
    IP_ADDRESS: KineticNodeType.IP_ADDRESS,
}


def build_graph(snapshot: AmlSnapshot, entity_id: str, hub_threshold: int) -> KineticNetworkGraph:
    edges_df = snapshot.world.edges
    mine = edges_df[edges_df["source_id"] == entity_id]
    degree = edges_df.groupby("target_id")["source_id"].nunique()
    nodes: dict[str, KineticNode] = {}
    edges: list[KineticEdge] = []
    reach: set[str] = set()
    volume = float(snapshot.facts.loc[entity_id, "dep_volume"])
    for rec in mine.itertuples(index=False):
        tok, deg = str(rec.target_id), int(degree[rec.target_id])
        suppressed = bool(rec.is_shared_context) or deg > hub_threshold
        nodes[tok] = _token_node(tok, str(rec.edge_type), deg, suppressed)
        edges.append(_token_edge(entity_id, tok, str(rec.edge_type), volume))
        reach |= set(edges_df.loc[edges_df["target_id"] == tok, "source_id"]) - {entity_id}
    ring_nodes, ring_edges = _ring(snapshot, entity_id)
    partner = _partner(snapshot, entity_id)
    seed = _seed(snapshot, entity_id, len(mine) + len(ring_edges) + len(partner[1]))
    all_nodes = [seed, *nodes.values(), *ring_nodes, *partner[0]]
    return KineticNetworkGraph(
        graph_id=f"graph_{entity_id}",
        seed_entity_id=entity_id,
        nodes=all_nodes,
        edges=[*edges, *ring_edges, *partner[1]],
        total_uncollapsed_entities=len(reach | _ring_members(snapshot, entity_id)) + 1,
    )


def _seed(snapshot: AmlSnapshot, entity_id: str, degree: int) -> KineticNode:
    flagged = snapshot.case_for(entity_id) is not None
    return KineticNode(
        node_id=entity_id,
        node_type=KineticNodeType.CLIENT_ACCOUNT,
        label=f"{'Suspect ' if flagged else ''}Account #{entity_id}",
        degree=degree,
    )


def _token_node(token: str, edge_type: str, degree: int, suppressed: bool) -> KineticNode:
    label = _token_label(token, edge_type, suppressed)
    return KineticNode(
        node_id=token,
        node_type=_NODE_TYPE[edge_type],
        label=label,
        degree=degree,
        is_hub_suppressed=suppressed,
        collapsed_node_count=max(degree - 1, 0) if suppressed else 0,
    )


def _token_label(token: str, edge_type: str, suppressed: bool) -> str:
    if token == PAYMENT_AGENT_HUB:
        return "Central Payment Gateway #007"
    if edge_type == IP_ADDRESS and suppressed:
        return f"Carrier CGNAT gateway {token[-6:]}"
    kind = {
        PAYMENT: "Shared payment method",
        DEVICE: "Shared device fingerprint",
        IP_ADDRESS: "Shared network address",
    }
    return f"{kind[edge_type]} {token[-6:]}"


def _token_edge(entity_id: str, token: str, edge_type: str, volume: float) -> KineticEdge:
    if edge_type == PAYMENT:
        return KineticEdge(
            source_node_id=entity_id,
            target_node_id=token,
            edge_type="TRANSACTION_FLOW",
            transaction_volume_usd=round(volume, 2),
        )
    return KineticEdge(
        source_node_id=entity_id,
        target_node_id=token,
        edge_type="SHARED_DEVICE" if edge_type == DEVICE else "SHARED_IP",
    )


def _ring_members(snapshot: AmlSnapshot, entity_id: str) -> set[str]:
    ring = snapshot.ring_of(entity_id)
    return set(ring.member_client_ids) - {entity_id} if ring else set()


def _ring(snapshot: AmlSnapshot, entity_id: str) -> tuple[list[KineticNode], list[KineticEdge]]:
    ring = snapshot.ring_of(entity_id)
    if ring is None:
        return [], []
    others = [m for m in ring.member_client_ids if m != entity_id]
    hub_id = f"COLLAPSED-{ring.cluster_id}"
    hub = KineticNode(
        node_id=hub_id,
        node_type=KineticNodeType.COLLAPSED_CLUSTER_HUB,
        label=f"Mule Syndicate Ring {ring.cluster_id[-4:]} (+{len(others)} Linked Accounts)",
        degree=ring.cluster_size,
        is_hub_suppressed=True,
        collapsed_node_count=len(others),
    )
    gaps = _timing_gaps(snapshot, entity_id, others)
    nearest = sorted(others, key=lambda m: (gaps.get(m, float("inf")), m))[:_MAX_MEMBERS_SHOWN]
    members = [
        KineticNode(
            node_id=m,
            node_type=KineticNodeType.CLIENT_ACCOUNT,
            label=f"Linked account #{m}",
            degree=1,
        )
        for m in nearest
    ]
    edges = [
        KineticEdge(
            source_node_id=entity_id,
            target_node_id=hub_id,
            edge_type="MATCHED_TIMING",
            matched_timing_seconds=_nearest(gaps),
        )
    ]
    edges += [
        KineticEdge(
            source_node_id=hub_id,
            target_node_id=m,
            edge_type="MATCHED_TIMING",
            matched_timing_seconds=gaps.get(m),
        )
        for m in nearest
    ]
    return [hub, *members], edges


def _timing_gaps(snapshot: AmlSnapshot, entity_id: str, others: list[str]) -> dict[str, float]:
    """Smallest gap in seconds between any deposit of the seed and any deposit of each member."""
    tx = snapshot.world.transactions
    dep = tx[tx["transaction_type"] == "DEPOSIT"]
    seed = dep.loc[dep["client_id"] == entity_id, "timestamp"].astype("int64").to_numpy() / 1e9
    gaps: dict[str, float] = {}
    for member, group in dep[dep["client_id"].isin(others)].groupby("client_id"):
        times = group["timestamp"].astype("int64").to_numpy() / 1e9
        if len(seed) and len(times):
            gaps[str(member)] = round(float(abs(seed[:, None] - times[None, :]).min()), 3)
    return gaps


def _nearest(gaps: dict[str, float]) -> float | None:
    return min(gaps.values()) if gaps else None


def _partner(snapshot: AmlSnapshot, entity_id: str) -> tuple[list[KineticNode], list[KineticEdge]]:
    partner = snapshot.facts.loc[entity_id, "partner_id"]
    if partner is None or (isinstance(partner, float) and pd.isna(partner)):
        return [], []
    node = KineticNode(
        node_id=str(partner),
        node_type=KineticNodeType.PARTNER_ACCOUNT,
        label=f"Partner Affiliate {partner}",
        degree=1,
    )
    return [node], [
        KineticEdge(source_node_id=str(partner), target_node_id=entity_id, edge_type="REFERRED")
    ]
