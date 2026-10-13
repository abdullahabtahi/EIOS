"""Persistent Action Outbox Ledger & Four-Eyes Dual-Signoff State Machine (ADR-017, T027)."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from eios.ontology.actions.bigquery_sync import BigQueryLedgerExporter
from eios.ontology.actions.models import (
    ActionSeverity,
    LedgerEventType,
)
from eios.ontology.actions.sequencer import LedgerSequencer


class FourEyesViolationError(Exception):
    """Raised when Four-Eyes dual approval principles are violated."""

    pass


class OutboxState(StrEnum):
    PENDING_PRIMARY_APPROVAL = "PENDING_PRIMARY_APPROVAL"
    PENDING_SECONDARY_APPROVAL = "PENDING_SECONDARY_APPROVAL"
    AUTHORIZED = "AUTHORIZED"
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"


class OutboxRecord(BaseModel):
    intent_id: str
    action_type: str
    target_entity_id: str
    severity: ActionSeverity
    initiator_id: str
    state: OutboxState
    primary_approver_id: str | None = None
    primary_approver_role: str | None = None
    secondary_approver_id: str | None = None
    secondary_approver_role: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    committed_at: datetime | None = None
    ledger_seq: int | None = None
    hash_chain: str | None = None


class PersistentActionOutboxLedger:
    """Outbox state machine governing two-phase commit actions with strict Four-Eyes separation."""

    def __init__(
        self,
        sequencer: LedgerSequencer | None = None,
        bq_exporter: BigQueryLedgerExporter | None = None,
    ) -> None:
        self.sequencer = sequencer or LedgerSequencer()
        self.bq_exporter = bq_exporter or BigQueryLedgerExporter()
        self._records: dict[str, OutboxRecord] = {}
        self._lock = threading.Lock()

    def stage_intent(
        self,
        action_type: str,
        target_entity_id: str,
        initiator_id: str,
        severity: ActionSeverity = ActionSeverity.HIGH,
    ) -> OutboxRecord:
        """Stages an action intent into the persistent outbox."""
        intent_id = f"intent_{uuid.uuid4().hex[:10]}"
        rec = OutboxRecord(
            intent_id=intent_id,
            action_type=action_type,
            target_entity_id=target_entity_id,
            severity=severity,
            initiator_id=initiator_id,
            state=OutboxState.PENDING_PRIMARY_APPROVAL,
        )
        with self._lock:
            self._records[intent_id] = rec
        return rec

    def submit_primary_approval(
        self,
        intent_id: str,
        approver_id: str,
        approver_role: str,
    ) -> OutboxRecord:
        """First signoff check. Enforces initiator cannot approve own intent."""
        with self._lock:
            if intent_id not in self._records:
                raise KeyError(f"Intent '{intent_id}' not found")
            rec = self._records[intent_id]

            if rec.initiator_id == approver_id:
                raise FourEyesViolationError(
                    f"Four-Eyes Violation: Initiator '{approver_id}' cannot approve own intent (Principle II)"
                )

            rec.primary_approver_id = approver_id
            rec.primary_approver_role = approver_role
            rec.state = OutboxState.PENDING_SECONDARY_APPROVAL
            return rec

    def submit_secondary_approval(
        self,
        intent_id: str,
        secondary_approver_id: str,
        secondary_approver_role: str,
    ) -> OutboxRecord:
        """Second signoff check. Enforces distinct approvers and distinct operational roles."""
        with self._lock:
            if intent_id not in self._records:
                raise KeyError(f"Intent '{intent_id}' not found")
            rec = self._records[intent_id]

            if rec.state != OutboxState.PENDING_SECONDARY_APPROVAL:
                raise FourEyesViolationError(
                    "Cannot submit secondary approval before primary approval"
                )

            if secondary_approver_id == rec.initiator_id:
                raise FourEyesViolationError(
                    f"Four-Eyes Violation: Initiator '{secondary_approver_id}' cannot be secondary approver"
                )

            if secondary_approver_id == rec.primary_approver_id:
                raise FourEyesViolationError(
                    f"Four-Eyes Violation: Primary approver '{secondary_approver_id}' cannot self-grant secondary approval"
                )

            if secondary_approver_role == rec.primary_approver_role:
                raise FourEyesViolationError(
                    f"Four-Eyes Violation: Secondary approval requires distinct operational role (found duplicate '{secondary_approver_role}')"
                )

            rec.secondary_approver_id = secondary_approver_id
            rec.secondary_approver_role = secondary_approver_role
            rec.state = OutboxState.AUTHORIZED

            # Atomically sequence into ledger
            ledger_entry = self.sequencer.record_event(
                event_type=LedgerEventType.APPROVAL_RECORDED,
                entity_id=rec.intent_id,
                payload={
                    "intent_id": rec.intent_id,
                    "initiator_id": rec.initiator_id,
                    "primary_approver": rec.primary_approver_id,
                    "secondary_approver": rec.secondary_approver_id,
                    "status": "AUTHORIZED",
                },
            )
            rec.ledger_seq = ledger_entry.ledger_seq
            rec.hash_chain = ledger_entry.current_hash
            rec.state = OutboxState.COMMITTED
            rec.committed_at = datetime.now(UTC)

            # Export to BigQuery Lakehouse sync buffer
            self.bq_exporter.stream_entry(ledger_entry)

            return rec
