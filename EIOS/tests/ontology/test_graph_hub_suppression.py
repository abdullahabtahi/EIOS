"""Test Hub Suppression filter and supernode isolation on property graph (T023)."""

from eios.ontology.graph.property_graph import InMemPropertyGraph


def test_hub_suppression_tagging_on_high_degree_nodes(seeded_hot_state):
    graph = InMemPropertyGraph(hub_threshold=5)
    graph.rehydrate_from_hot_state(seeded_hot_state)

    # DEV-HUB is connected to C-1001..C-1006 (6 clients >= 5)
    node_data = graph.get_node_data("DEV-HUB")
    assert node_data["is_shared_context"] is True
    assert node_data["degree"] >= 5

    # DEV-RING-1 is connected to C-1011..C-1013 (3 clients < 5)
    ring_node_data = graph.get_node_data("DEV-RING-1")
    assert ring_node_data["is_shared_context"] is False
    assert ring_node_data["degree"] == 3


def test_ego_graph_pruning_with_hub_suppression(seeded_hot_state):
    graph = InMemPropertyGraph(hub_threshold=5)
    graph.rehydrate_from_hot_state(seeded_hot_state)

    # With suppress_hubs=True, traversal from C-1001 should NOT cascade
    # through DEV-HUB to C-1002..C-1006
    ego_suppressed = graph.get_ego_graph(seed_id="C-1001", hops=2, suppress_hubs=True)
    assert "C-1001" in ego_suppressed["nodes"]
    # DEV-HUB may be adjacent, but other clients sharing DEV-HUB MUST be excluded
    for other_client in ["C-1002", "C-1003", "C-1004", "C-1005", "C-1006"]:
        assert other_client not in ego_suppressed["nodes"]

    # With suppress_hubs=False, traversal DOES include other clients sharing DEV-HUB
    ego_unsuppressed = graph.get_ego_graph(seed_id="C-1001", hops=2, suppress_hubs=False)
    assert "C-1002" in ego_unsuppressed["nodes"]
