"""What the investigator's inspector shows for each node of a case's network, computed from that network (spec 031).

Centrality and clustering come from the displayed graph itself. A client's risk is its own strongest alert, its
jurisdiction its KYC country and its velocity its 30-day deposits. A token or gateway has no risk of its own, so none
is claimed.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from eios.cockpit.aml import KineticNetworkGraph, KineticNodeType
from eios.dataplane.aml_engine import AmlSnapshot

_PLACES = 3


def node_insights(snapshot: AmlSnapshot, graph: KineticNetworkGraph) -> dict[str, dict[str, Any]]:
    view = nx.Graph()
    view.add_nodes_from(n.node_id for n in graph.nodes)
    view.add_edges_from((e.source_node_id, e.target_node_id) for e in graph.edges)
    between = nx.betweenness_centrality(view)
    cluster = nx.clustering(view)
    risk_of = _strongest_risk(snapshot)
    out: dict[str, dict[str, Any]] = {}
    for node in graph.nodes:
        row: dict[str, Any] = {
            "betweenness": round(float(between[node.node_id]), _PLACES),
            "clustering": round(float(cluster[node.node_id]), _PLACES),
            "links_in_view": int(view.degree[node.node_id]),
            "risk": None,
            "country": None,
            "velocity_usd": None,
        }
        if (
            node.node_type is KineticNodeType.CLIENT_ACCOUNT
            and node.node_id in snapshot.facts.index
        ):
            facts = snapshot.facts.loc[node.node_id]
            row["risk"] = risk_of.get(node.node_id)
            row["country"] = str(facts["country"])
            row["velocity_usd"] = round(float(facts["dep_volume"]), 2)
        out[node.node_id] = row
    return out


def _strongest_risk(snapshot: AmlSnapshot) -> dict[str, float]:
    best: dict[str, float] = {}
    for alert in snapshot.alerts:
        best[alert.client_id] = max(best.get(alert.client_id, 0.0), alert.risk_score)
    return best
