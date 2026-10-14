"""Who is calling, and from which workstation (spec 023, defect B3).

`uid` comes from the verified token, never from the request body or the question text. One rule covers
everything today: any verified operator may use any workstation, and the workstation only selects which
capabilities the assistant is offered. The rule is a single function so a real entitlement table can replace
it later without touching callers. Known limit: the workstation is a client choice, so it scopes the
assistant's tools but is not yet a boundary between people.
"""

from enum import StrEnum

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.omcp.port.contracts import PortError, ToolErrorCode

DEV_UID = (
    "dev-anonymous"  # trusted-anonymous local mode only; the auth layer refuses it when deployed
)


class Workstation(StrEnum):
    AML_INVESTIGATOR = "aml_investigator"
    PARTNER_MANAGER = "partner_manager"
    EXECUTIVE = "executive"
    COMPLIANCE_AUDITOR = "compliance_auditor"
    DATA_OPERATIONS = "data_operations"


class Principal(StrictModel):
    uid: str = Field(min_length=1)
    workstation: Workstation


def entitled_workstations(uid: str | None) -> frozenset[Workstation]:
    """The one entitlement rule: every operator may use every workstation."""
    return frozenset(Workstation)


def principal_for(uid: str | None, workstation: str) -> Principal:
    """Build the principal for a request; an unknown workstation is refused, never defaulted."""
    try:
        chosen = Workstation(workstation)
    except ValueError:
        raise PortError(ToolErrorCode.INVALID_ARGUMENTS, "unknown workstation") from None
    resolved_uid = uid or DEV_UID
    if chosen not in entitled_workstations(resolved_uid):
        raise PortError(
            ToolErrorCode.FORBIDDEN_ROLE, "operator is not entitled to this workstation"
        )
    return Principal(uid=resolved_uid, workstation=chosen)
