"""9 Canonical Link Types and bidirectional link navigation (US2)."""

from collections import defaultdict
from typing import Any

from eios.ontology.core.base import OntologyLink

# 9 Canonical Link Types
CANONICAL_LINK_TYPES = {
    "USES_DEVICE": ("ClientAccount", "Device", "MANY_TO_MANY"),
    "CONNECTS_FROM": ("ClientAccount", "IPAddress", "MANY_TO_MANY"),
    "FUNDS_VIA": ("ClientAccount", "PaymentMethod", "MANY_TO_MANY"),
    "REFERRED_BY": ("ClientAccount", "Partner", "MANY_TO_ONE"),
    "SUB_OF": ("SubAffiliate", "Partner", "MANY_TO_ONE"),
    "COMPETES_IN": ("Competitor", "Region", "MANY_TO_MANY"),
    "AFFECTS": ("MacroEvent", "Partner", "MANY_TO_MANY"),
    "RAISED": ("Alert", "Case", "MANY_TO_ONE"),
    "DECIDED": ("Decision", "Case", "MANY_TO_ONE"),
}


class OntologyLinkGraph:
    """In-memory bidirectional relationship graph for Kinetic Ontology links."""

    def __init__(self) -> None:
        # Key: source_id -> list of OntologyLink
        self._forward_links: dict[str, list[OntologyLink]] = defaultdict(list)
        # Key: target_id -> list of OntologyLink
        self._reverse_links: dict[str, list[OntologyLink]] = defaultdict(list)

    def add_link(
        self,
        link_type: str,
        source_id: str,
        target_id: str,
        cardinality: str = "MANY_TO_MANY",
        metadata: dict[str, Any] | None = None,
    ) -> OntologyLink:
        """Add a typed relationship link between two entities."""
        link = OntologyLink(
            link_type=link_type,
            source_id=source_id,
            target_id=target_id,
            cardinality=cardinality,
            metadata=metadata or {},
        )
        self._forward_links[source_id].append(link)
        self._reverse_links[target_id].append(link)
        return link

    def get_target_links(self, source_id: str, link_type: str | None = None) -> list[OntologyLink]:
        """Get all outbound links from source entity, optionally filtered by link type."""
        links = self._forward_links.get(source_id, [])
        if link_type:
            return [lnk for lnk in links if lnk.link_type == link_type]
        return links

    def get_source_links(self, target_id: str, link_type: str | None = None) -> list[OntologyLink]:
        """Get all inbound links to target entity, optionally filtered by link type."""
        links = self._reverse_links.get(target_id, [])
        if link_type:
            return [lnk for lnk in links if lnk.link_type == link_type]
        return links
