"""Workstation View Session Manager and Role-Based Access Control (RBAC)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from eios.cockpit.schemas import validate_contract


class OperatorRole(str, Enum):
    EXECUTIVE = "EXECUTIVE"
    AML_INVESTIGATOR = "AML_INVESTIGATOR"
    PARTNER_MANAGER = "PARTNER_MANAGER"
    COMPLIANCE_AUDITOR = "COMPLIANCE_AUDITOR"
    DATA_OPERATIONS = "DATA_OPERATIONS"


class WorkstationTab(str, Enum):
    EXECUTIVE_SYNTHESIS = "EXECUTIVE_SYNTHESIS"
    AML_TRIAGE_DOSSIER = "AML_TRIAGE_DOSSIER"
    PARTNER_CHURN_RADAR = "PARTNER_CHURN_RADAR"
    COMPLIANCE_LEDGER = "COMPLIANCE_LEDGER"
    DATA_OPS_BOARD = "DATA_OPS_BOARD"


ROLE_TAB_PERMISSIONS: dict[OperatorRole, set[WorkstationTab]] = {
    OperatorRole.EXECUTIVE: {
        WorkstationTab.EXECUTIVE_SYNTHESIS,
        WorkstationTab.AML_TRIAGE_DOSSIER,
        WorkstationTab.PARTNER_CHURN_RADAR,
        WorkstationTab.COMPLIANCE_LEDGER,
        WorkstationTab.DATA_OPS_BOARD,
    },
    OperatorRole.AML_INVESTIGATOR: {
        WorkstationTab.AML_TRIAGE_DOSSIER,
        WorkstationTab.COMPLIANCE_LEDGER,
    },
    OperatorRole.PARTNER_MANAGER: {
        WorkstationTab.PARTNER_CHURN_RADAR,
        WorkstationTab.COMPLIANCE_LEDGER,
    },
    OperatorRole.COMPLIANCE_AUDITOR: {
        WorkstationTab.COMPLIANCE_LEDGER,
        WorkstationTab.AML_TRIAGE_DOSSIER,
        WorkstationTab.PARTNER_CHURN_RADAR,
    },
    OperatorRole.DATA_OPERATIONS: {
        WorkstationTab.DATA_OPS_BOARD,
        WorkstationTab.COMPLIANCE_LEDGER,
    },
}

DEFAULT_TAB_PER_ROLE: dict[OperatorRole, WorkstationTab] = {
    OperatorRole.EXECUTIVE: WorkstationTab.EXECUTIVE_SYNTHESIS,
    OperatorRole.AML_INVESTIGATOR: WorkstationTab.AML_TRIAGE_DOSSIER,
    OperatorRole.PARTNER_MANAGER: WorkstationTab.PARTNER_CHURN_RADAR,
    OperatorRole.COMPLIANCE_AUDITOR: WorkstationTab.COMPLIANCE_LEDGER,
    OperatorRole.DATA_OPERATIONS: WorkstationTab.DATA_OPS_BOARD,
}


class WorkstationViewSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operator_id: str
    role: OperatorRole
    active_tab: WorkstationTab
    applied_filters: dict[str, str] = Field(default_factory=dict)
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_contract_dict(self) -> dict[str, Any]:
        data = {
            "session_id": self.session_id,
            "operator_id": self.operator_id,
            "role": self.role.value,
            "active_tab": self.active_tab.value,
            "applied_filters": self.applied_filters,
            "last_active_at": self.last_active_at.isoformat(),
        }
        validate_contract(data, "workstation-view-session")
        return data


class SessionManager:
    """Manages active operator workstation sessions and enforces RBAC."""

    def __init__(self) -> None:
        self._sessions: dict[str, WorkstationViewSession] = {}

    def create_session(
        self,
        operator_id: str,
        role: OperatorRole,
        active_tab: WorkstationTab | None = None,
    ) -> WorkstationViewSession:
        if active_tab is None or active_tab not in ROLE_TAB_PERMISSIONS[role]:
            active_tab = DEFAULT_TAB_PER_ROLE[role]

        session = WorkstationViewSession(
            operator_id=operator_id,
            role=role,
            active_tab=active_tab,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> WorkstationViewSession | None:
        return self._sessions.get(session_id)

    def switch_tab(self, session_id: str, new_tab: WorkstationTab) -> WorkstationViewSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        if new_tab not in ROLE_TAB_PERMISSIONS[session.role]:
            raise PermissionError(
                f"Role {session.role.value} does not have access to tab {new_tab.value}"
            )

        session.active_tab = new_tab
        session.last_active_at = datetime.now(UTC)
        return session

    def update_filters(self, session_id: str, filters: dict[str, str]) -> WorkstationViewSession:
        session = self._sessions.get(session_id)
        if not session:
            raise KeyError(f"Session {session_id} not found")

        session.applied_filters.update(filters)
        session.last_active_at = datetime.now(UTC)
        return session
