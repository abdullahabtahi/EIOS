"""Hub Suppression Filter preventing false merges on shared devices/IPs (ADR-008, US4)."""

from collections import defaultdict
import threading


class HubSuppressionFilter:
    """Detects high-degree attribute nodes (e.g. shared family devices, office CGNAT IPs)."""

    def __init__(self, degree_threshold: int = 5) -> None:
        self.degree_threshold = degree_threshold
        # Key: (attribute_type, attribute_value) -> Set of distinct tax_ids/identities
        self._associations: dict[tuple[str, str], set[str]] = defaultdict(set)
        self._lock = threading.Lock()

    def register_association(
        self,
        attribute_type: str,
        attribute_value: str,
        tax_id: str,
    ) -> bool:
        """Register that a given tax_id / identity connected via an attribute (device or IP)."""
        key = (attribute_type, attribute_value)
        with self._lock:
            self._associations[key].add(tax_id)
            return len(self._associations[key]) >= self.degree_threshold

    def is_shared_context(self, attribute_type: str, attribute_value: str) -> bool:
        """Check if an attribute node has reached the hub threshold (degree >= 5)."""
        key = (attribute_type, attribute_value)
        with self._lock:
            return len(self._associations.get(key, set())) >= self.degree_threshold

    def get_degree(self, attribute_type: str, attribute_value: str) -> int:
        """Get the number of distinct entities connected to an attribute."""
        key = (attribute_type, attribute_value)
        with self._lock:
            return len(self._associations.get(key, set()))
