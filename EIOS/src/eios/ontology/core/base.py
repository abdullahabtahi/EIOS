"""Foundational base classes and descriptors for the Kinetic Ontology."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from eios.ontology.config import SecurityMarking


class OntologyObject(BaseModel, ABC):
    """Base class for all Kinetic Ontology Object Types."""

    markings: list[SecurityMarking] = Field(default_factory=list)

    @property
    @abstractmethod
    def primary_key(self) -> str:
        """Unique object identifier."""
        pass

    def has_marking(self, marking: SecurityMarking) -> bool:
        """Check if this object carries the specified security marking."""
        return marking in self.markings

    def to_dict(self) -> dict[str, Any]:
        """Serialize object to dictionary with stringified markings."""
        dumped = self.model_dump(mode="json")
        dumped["markings"] = [
            m.value if isinstance(m, SecurityMarking) else str(m) for m in self.markings
        ]
        return dumped


class OntologyLink(BaseModel):
    """Represents a typed relationship between two Ontology objects."""

    link_type: str
    source_id: str
    target_id: str
    cardinality: str = "MANY_TO_MANY"  # ONE_TO_ONE, ONE_TO_MANY, MANY_TO_ONE, MANY_TO_MANY
    metadata: dict[str, Any] = Field(default_factory=dict)
