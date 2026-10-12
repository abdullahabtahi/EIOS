"""Hub Suppression Filter for NetworkX Property Graph (ADR-008, US3)."""

from typing import Any


class GraphHubSuppressionFilter:
    """Evaluates node degrees and flags supernode context nodes to prevent false merges."""

    def __init__(self, degree_threshold: int = 5) -> None:
        self.degree_threshold = degree_threshold

    def evaluate_node(self, node_id: str, node_type: str, degree: int) -> dict[str, Any]:
        """Determine if a node is a shared context hub based on type and degree."""
        is_context_type = node_type in ["Device", "IPAddress"] or node_id.startswith(
            ("DEV-", "IP-")
        )
        is_hub = is_context_type and (degree >= self.degree_threshold)
        return {
            "is_shared_context": is_hub,
            "degree": degree,
            "hub_badge": "SHARED_CONTEXT_HUB" if is_hub else None,
        }

    def should_suppress_traversal(
        self,
        current_node_id: str,
        current_node_data: dict[str, Any],
        target_node_id: str,
        target_node_data: dict[str, Any],
    ) -> bool:
        """Return True if traversal through current or target node should be suppressed."""
        if current_node_data.get("is_shared_context", False):
            return True
        return False
