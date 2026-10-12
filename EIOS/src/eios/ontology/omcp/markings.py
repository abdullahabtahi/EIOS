"""Security marking enforcer and redaction gateway for OMCP (US7).

Enforces server-side mandatory security markings (PII, SENSITIVE_COMPLIANCE,
PARTNER_COMMERCIAL) based on caller role clearance, per Constitution Principle IV.
"""

from typing import Any

from eios.ontology.config import SecurityMarking
from eios.ontology.core.base import OntologyObject


class InsufficientMarkingError(PermissionError):
    """Raised when a caller lacks required security marking clearance."""

    pass


class SecurityMarkingEnforcer:
    """Evaluates caller security clearance against security markings."""

    # Role clearance matrix mapping roles to authorized markings
    ROLE_CLEARANCE: dict[str, set[SecurityMarking]] = {
        "AMLInvestigator": {SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE},
        "MLRO": {
            SecurityMarking.PII,
            SecurityMarking.SENSITIVE_COMPLIANCE,
            SecurityMarking.PARTNER_COMMERCIAL,
        },
        "ComplianceOfficer": {SecurityMarking.PII, SecurityMarking.SENSITIVE_COMPLIANCE},
        "PartnerManager": {SecurityMarking.PII, SecurityMarking.PARTNER_COMMERCIAL},
        "HeadOfPartnerships": {SecurityMarking.PII, SecurityMarking.PARTNER_COMMERCIAL},
        "Executive": {
            SecurityMarking.PII,
            SecurityMarking.SENSITIVE_COMPLIANCE,
            SecurityMarking.PARTNER_COMMERCIAL,
        },
        "Admin": {
            SecurityMarking.PII,
            SecurityMarking.SENSITIVE_COMPLIANCE,
            SecurityMarking.PARTNER_COMMERCIAL,
        },
        "PublicAgent": set(),
        "Public": set(),
    }

    # Attributes that must be redacted when PII clearance is absent
    PII_ATTRIBUTES: set[str] = {
        "full_name",
        "email",
        "phone",
        "tax_id",
        "dob",
        "declared_monthly_income",
    }

    def __init__(self, caller_role: str = "PublicAgent") -> None:
        self.caller_role = caller_role
        self.clearance = self.ROLE_CLEARANCE.get(caller_role, set())

    def can_access(self, marking: SecurityMarking | str) -> bool:
        """Check if caller has clearance for a given marking."""
        if isinstance(marking, str):
            try:
                marking = SecurityMarking(marking)
            except ValueError:
                return False
        return marking in self.clearance

    def _resolve_markings(self, raw_markings: list[Any]) -> set[SecurityMarking]:
        """Normalize markings to SecurityMarking enum set."""
        resolved: set[SecurityMarking] = set()
        for m in raw_markings:
            if isinstance(m, SecurityMarking):
                resolved.add(m)
            elif isinstance(m, str) and m in SecurityMarking.__members__:
                resolved.add(SecurityMarking(m))
        return resolved

    def _assert_clearance(self, markings: set[SecurityMarking]) -> None:
        """Assert caller holds clearance for all classified markings."""
        if SecurityMarking.SENSITIVE_COMPLIANCE in markings:
            if SecurityMarking.SENSITIVE_COMPLIANCE not in self.clearance:
                raise InsufficientMarkingError(
                    f"Caller '{self.caller_role}' lacks SENSITIVE_COMPLIANCE clearance."
                )

        if SecurityMarking.PARTNER_COMMERCIAL in markings:
            if SecurityMarking.PARTNER_COMMERCIAL not in self.clearance:
                raise InsufficientMarkingError(
                    f"Caller '{self.caller_role}' lacks PARTNER_COMMERCIAL clearance."
                )

    def filter_entity(self, entity: OntologyObject | dict[str, Any]) -> dict[str, Any]:
        """Filter an ontology object representation according to role clearance."""
        if isinstance(entity, OntologyObject):
            raw_markings = entity.markings
            data = entity.to_dict()
        elif isinstance(entity, dict):
            raw_markings = entity.get("markings", [])
            data = dict(entity)
        else:
            raise TypeError(f"Expected OntologyObject or dict, got {type(entity)}")

        resolved_markings = self._resolve_markings(raw_markings)
        self._assert_clearance(resolved_markings)

        filtered_data = dict(data)
        if SecurityMarking.PII not in self.clearance:
            for attr in self.PII_ATTRIBUTES:
                if attr in filtered_data:
                    filtered_data[attr] = "[REDACTED]"

        filtered_data["markings"] = [
            m.value if isinstance(m, SecurityMarking) else str(m) for m in raw_markings
        ]
        return filtered_data
