"""Test in-memory NetworkX Property Graph and cold-boot rehydration (T022)."""

import time

from eios.ontology.graph.property_graph import InMemPropertyGraph


def test_property_graph_rehydration_from_hot_state(seeded_hot_state):
    graph = InMemPropertyGraph()
    t0 = time.perf_counter()
    graph.rehydrate_from_hot_state(seeded_hot_state)
    duration = time.perf_counter() - t0

    assert duration < 1.5, f"Rehydration took {duration:.2f}s, expected < 1.5s"
    assert graph.node_count > 0
    assert graph.edge_count > 0
    assert graph.has_node("C-1001")
    assert graph.has_node("DEV-HUB")


def test_ego_graph_traversal_sub_25ms(seeded_hot_state):
    graph = InMemPropertyGraph()
    graph.rehydrate_from_hot_state(seeded_hot_state)

    t0 = time.perf_counter()
    ego = graph.get_ego_graph(seed_id="C-1011", hops=2, suppress_hubs=True)
    traversal_ms = (time.perf_counter() - t0) * 1000.0

    assert traversal_ms < 25.0, f"Ego-graph traversal took {traversal_ms:.2f}ms, expected < 25ms"
    assert "C-1011" in ego["nodes"]
    assert "DEV-RING-1" in ego["nodes"]


def test_community_detection_identifies_cliques(seeded_hot_state):
    graph = InMemPropertyGraph()
    graph.rehydrate_from_hot_state(seeded_hot_state)

    communities = graph.detect_communities(suppress_hubs=True)
    assert len(communities) >= 1
    # Check that C-1011, C-1012, C-1013 belong to the same ring community
    ring_comm = None
    for comm in communities:
        if "C-1011" in comm:
            ring_comm = comm
            break
    assert ring_comm is not None
    assert "C-1012" in ring_comm
    assert "C-1013" in ring_comm
