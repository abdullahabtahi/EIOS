"""Polymorphic Interfaces for Kinetic Ontology objects per docs/foundry.md."""

from abc import ABC, abstractmethod
from typing import Any


class TransactingEntity(ABC):
    """Interface for entities participating in financial flows (ClientAccount, Partner)."""

    @abstractmethod
    def get_total_volume(self, window: str = "30d") -> float:
        """Calculate total transacted gross volume."""
        pass

    @abstractmethod
    def get_net_flow(self, window: str = "30d") -> float:
        """Calculate net deposit/withdrawal or commission flow."""
        pass

    @abstractmethod
    def get_risk_rating(self) -> str:
        """Return categorical risk rating."""
        pass


class AuditableEntity(ABC):
    """Interface for entities maintaining regulatory audit trails (Case, Alert, Decision)."""

    @abstractmethod
    def get_audit_trail(self) -> list[dict[str, Any]]:
        """Return immutable chronological sequence of changes/decisions."""
        pass

    @abstractmethod
    def get_security_markings(self) -> list[str]:
        """Return security markings governing access."""
        pass
