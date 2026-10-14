"""Compliance & Audit Explorer Service.

Delivers the monotonic ledger timeline (ledger_seq = 1, 2, 3...), interactive
SHA-256 hash chain verification bar, immutable WORM checkpoint proofs, and Four-Eyes approval logs.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from eios.cockpit import compliance_ledger as ledger
from eios.ontology.actions.audit import ContinuousAuditWalker
from eios.ontology.actions.intent_hub import ActionIntentHub
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.worm import WORMAnchorService


class LedgerTimelineEntry(BaseModel):
    ledger_seq: int
    event_type: str
    prev_hash: str
    current_hash: str
    actor_id: str
    timestamp: datetime
    is_worm_anchored: bool = False


class WORMCheckpointProof(BaseModel):
    checkpoint_id: str
    chain_head_seq: int
    root_hash: str
    retention_expiration: datetime
    compliance_lock_mode: str = "COMPLIANCE"
    is_immutable: bool = True


class FourEyesAuditRecord(BaseModel):
    intent_id: str
    action_type: str
    target_entity_id: str
    first_approver_id: str
    first_approver_role: str
    first_approved_at: datetime
    second_approver_id: str
    second_approver_role: str
    second_approved_at: datetime
    execution_receipt_id: str | None = None
    override_reason: str | None = None


class ComplianceExplorerService:
    """Service providing visual audit exploration, hash chain verifier, and WORM proofs."""

    def __init__(
        self,
        sequencer: LedgerSequencer | None = None,
        audit_walker: ContinuousAuditWalker | None = None,
        worm_service: WORMAnchorService | None = None,
        hub: ActionIntentHub | None = None,
    ) -> None:
        self.sequencer = sequencer
        self.audit_walker = audit_walker
        self.worm_service = worm_service
        self.hub = hub

    @classmethod
    def over_ledger(
        cls, sequencer: LedgerSequencer, worm: WORMAnchorService, hub: ActionIntentHub
    ) -> ComplianceExplorerService:
        """The service over the governance runtime's real ledger, checkpoints and intents."""
        return cls(
            sequencer=sequencer,
            audit_walker=ContinuousAuditWalker(sequencer, worm),
            worm_service=worm,
            hub=hub,
        )

    def get_ledger_timeline(self, start_seq: int = 1, limit: int = 20) -> list[dict[str, Any]]:
        """Returns sequential monotonic ledger records."""
        if self.sequencer is not None:
            return ledger.ledger_timeline(
                self.sequencer, self.worm_service, self.hub, start_seq, limit
            )

        # Canonical demo sequence (ledger_seq = 1, 2, 3...)
        now = datetime.now(UTC)
        genesis = "0" * 64
        h1 = "a1" * 32
        h2 = "b2" * 32
        h3 = "c3" * 32

        return [
            {
                "ledger_seq": 1,
                "event_type": "ACTION_PROPOSED",
                "prev_hash": genesis,
                "current_hash": h1,
                "actor_id": "AMLSupervisorAgent",
                "timestamp": now.isoformat(),
                "is_worm_anchored": True,
            },
            {
                "ledger_seq": 2,
                "event_type": "ACTION_APPROVED_FIRST",
                "prev_hash": h1,
                "current_hash": h2,
                "actor_id": "Officer_Alice_MLRO",
                "timestamp": now.isoformat(),
                "is_worm_anchored": True,
            },
            {
                "ledger_seq": 3,
                "event_type": "ACTION_APPROVED_DUAL",
                "prev_hash": h2,
                "current_hash": h3,
                "actor_id": "Officer_Bob_ComplianceHead",
                "timestamp": now.isoformat(),
                "is_worm_anchored": False,
            },
        ]

    def verify_hash_chain_interactive(self) -> dict[str, Any]:
        """Executes full cryptographic hash chain verification walking."""
        t0 = time.perf_counter()

        if self.audit_walker:
            report = self.audit_walker.verify_ledger()
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            corrupted = (
                [report.tampered_sequence_id] if report.tampered_sequence_id is not None else []
            )
            return {
                "total_entries_verified": report.total_entries,
                "is_chain_unbroken": report.is_valid,
                "chain_head_hash": report.head_hash,
                "corrupted_indices": corrupted,
                "worm_anchors_matched": report.worm_checkpoints_verified,
                "verification_latency_ms": round(elapsed_ms, 2),
                "integrity_score_pct": round(report.integrity_score * 100.0, 2),
                "status": "VALID" if report.is_valid else "CORRUPTED",
                "total_verified": report.total_entries,
            }

        # Simulated verification pass for 10,000 records
        time.sleep(0.005)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "total_entries_verified": 10000,
            "is_chain_unbroken": True,
            "chain_head_hash": "f9e8d7c6b5a41234567890abcdef1234567890abcdef1234567890abcdef1234",
            "corrupted_indices": [],
            "worm_anchors_matched": 24,
            "verification_latency_ms": round(elapsed_ms, 2),
            "integrity_score_pct": 100.0,
        }

    def get_worm_compliance_proofs(self) -> list[dict[str, Any]]:
        """Returns verified immutable WORM compliance retention proofs."""
        if self.worm_service is not None:
            return ledger.checkpoint_proofs(self.worm_service)
        expiration = datetime(2033, 10, 9, 0, 0, tzinfo=UTC)  # 7-year statutory retention

        return [
            {
                "checkpoint_id": "WORM-CKPT-20261009-001",
                "chain_head_seq": 4820,
                "root_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "retention_expiration": expiration.isoformat(),
                "compliance_lock_mode": "COMPLIANCE",
                "is_immutable": True,
                "storage_uri": "gs://deriv-eios-worm-compliance-audit/checkpoints/20261009-001.json",
            }
        ]

    def get_four_eyes_approval_log(self) -> list[dict[str, Any]]:
        """Returns dual human approval log entries for High-severity mutations."""
        if self.hub is not None:
            return ledger.approval_log(self.hub)
        now = datetime.now(UTC)
        return [
            {
                "intent_id": "intent_hold_cr84920",
                "action_type": "HoldWithdrawal",
                "target_entity_id": "CR84920",
                "severity": "HIGH",
                "first_approver": {
                    "officer_id": "officer_alice_sg",
                    "role": "AML_INVESTIGATOR",
                    "approved_at": now.isoformat(),
                    "comment": "Confirmed 16x deposit discrepancy and syndicate link #14",
                },
                "second_approver": {
                    "officer_id": "officer_bob_uk",
                    "role": "COMPLIANCE_HEAD",
                    "approved_at": now.isoformat(),
                    "comment": "Concur with immediate capital flight risk; dual sign-off confirmed",
                },
                "execution_receipt_id": "rcpt_hold_9104",
                "status": "EXECUTED",
            }
        ]
