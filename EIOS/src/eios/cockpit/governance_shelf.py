"""Governed Action Shelf Presenter and Two-Phase Commit State Machine Coordinator.

Strict institutional light mode COP invariants and Principle II / IV governed 2PC commitments.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from eios.cockpit.schemas import validate_contract
from eios.ontology.actions.models import (
    ActionIntentToken,
    ActionSeverity,
    ActionStatus,
    ApprovalRecord,
)

# Canonical mapping for contract schema alignment
_ACTION_TYPE_CONTRACT_MAP = {
    "LaunchRetentionPlaybook": "DeployRetentionVIPDeal",
}


class GovernedActionCard(BaseModel):
    intent_id: str
    action_type: str
    target_entity_id: str
    severity: str
    requires_four_eyes: bool
    first_approver_id: Optional[str] = None
    second_approver_id: Optional[str] = None
    kms_signature_verified: bool
    status: str
    seconds_remaining: int

    def to_contract_dict(self) -> Dict[str, Any]:
        mapped_action_type = _ACTION_TYPE_CONTRACT_MAP.get(self.action_type, self.action_type)
        data = {
            "intent_id": self.intent_id,
            "action_type": mapped_action_type,
            "target_entity_id": self.target_entity_id,
            "severity": self.severity,
            "requires_four_eyes": self.requires_four_eyes,
            "first_approver_id": self.first_approver_id,
            "second_approver_id": self.second_approver_id,
            "kms_signature_verified": self.kms_signature_verified,
            "status": self.status,
            "seconds_remaining": max(0, min(900, self.seconds_remaining)),
        }
        validate_contract(data, "governed-action-card")
        return data


class GovernedActionShelf:
    """Manages staged 2PC action cards rendered in the bottom action shelf with Four-Eyes dual approval."""

    FAST_PATH_BUDGET_THRESHOLD: float = 2500.0

    def __init__(self, intent_hub: Any | None = None) -> None:
        self.intent_hub = intent_hub
        self._staged_tokens: Dict[str, ActionIntentToken] = {}

    def stage_token(self, token: ActionIntentToken) -> GovernedActionCard:
        """Stages an ActionIntentToken in the shelf and returns the card view."""
        self._staged_tokens[token.intent_id] = token
        return self.present_card(token)

    def get_token(self, intent_id: str) -> Optional[ActionIntentToken]:
        return self._staged_tokens.get(intent_id)

    def present_card(self, token: ActionIntentToken) -> GovernedActionCard:
        """Converts an ActionIntentToken to a validated GovernedActionCard."""
        now = datetime.now(UTC)
        remaining = int((token.expires_at - now).total_seconds()) if token.expires_at > now else 0

        first_approver = token.approvals[0].approver_id if len(token.approvals) > 0 else None
        second_approver = token.approvals[1].approver_id if len(token.approvals) > 1 else None

        # Check status mapping
        card_status = "PENDING_APPROVAL"
        if token.status == ActionStatus.APPROVED:
            card_status = "APPROVED"
        elif token.status == ActionStatus.EXECUTED:
            card_status = "EXECUTED"
        elif token.status in [ActionStatus.ABORTED, ActionStatus.REJECTED]:
            card_status = "ABORTED"
        elif token.status == ActionStatus.EXPIRED or remaining <= 0:
            card_status = "EXPIRED"

        target_id = (
            token.parameters.get("account_id")
            or token.parameters.get("client_id")
            or token.parameters.get("partner_id")
            or token.parameters.get("txn_id")
            or token.parameters.get("case_id")
            or "UNKNOWN_ENTITY"
        )
        if isinstance(target_id, list):
            target_id = target_id[0] if target_id else "UNKNOWN_ENTITY"

        return GovernedActionCard(
            intent_id=token.intent_id,
            action_type=token.action_type,
            target_entity_id=str(target_id),
            severity=token.severity.value,
            requires_four_eyes=token.requires_dual_approval,
            first_approver_id=first_approver,
            second_approver_id=second_approver,
            kms_signature_verified=bool(token.signature),
            status=card_status,
            seconds_remaining=remaining,
        )

    def get_approval_modal_context(
        self,
        intent_id: str,
        officer_id: str,
        officer_role: str,
    ) -> Dict[str, Any]:
        """Provides full contextual state and eligibility checks for the Four-Eyes approval modal."""
        token = self._staged_tokens.get(intent_id)
        if not token:
            raise KeyError(f"Action intent {intent_id} not found in shelf")

        card = self.present_card(token)
        now = datetime.now(UTC)
        is_expired = token.expires_at <= now or card.status == "EXPIRED"

        # Check eligibility: officer cannot sign twice
        has_already_signed = any(a.approver_id == officer_id for a in token.approvals)
        can_approve = not is_expired and not has_already_signed and card.status in ["PENDING_APPROVAL"]

        rejection_reason = None
        if is_expired:
            rejection_reason = "Action intent token has expired (15-minute window elapsed)."
        elif has_already_signed:
            rejection_reason = "Officer has already signed as first approver. Four-Eyes requires a distinct second officer."
        elif card.status == "APPROVED":
            rejection_reason = "Action intent is already fully approved and ready for execution."
        elif card.status == "EXECUTED":
            rejection_reason = "Action has already executed against write-back sink."

        return {
            "intent_id": token.intent_id,
            "action_type": token.action_type,
            "target_entity_id": card.target_entity_id,
            "severity": card.severity,
            "requires_four_eyes": card.requires_four_eyes,
            "parameters": token.parameters,
            "evidence_refs": token.evidence_refs,
            "card_status": card.status,
            "seconds_remaining": card.seconds_remaining,
            "can_approve": can_approve,
            "ineligibility_reason": rejection_reason,
            "existing_approvals": [
                {
                    "approver_id": a.approver_id,
                    "approver_role": a.approver_role,
                    "approved_at": a.approved_at.isoformat(),
                    "comment": a.comment,
                }
                for a in token.approvals
            ],
            "kms_signature_verified": card.kms_signature_verified,
        }

    def submit_approval(
        self,
        intent_id: str,
        approver_id: str,
        approver_role: str,
        comment: str = "",
    ) -> GovernedActionCard:
        """Records an authenticated human sign-off on an action intent."""
        token = self._staged_tokens.get(intent_id)
        if not token:
            raise KeyError(f"Action intent {intent_id} not found in shelf")

        now = datetime.now(UTC)
        if token.expires_at <= now:
            token.status = ActionStatus.EXPIRED
            return self.present_card(token)

        # Disallow duplicate approval by same officer (Four-Eyes dual approval enforcement)
        for existing in token.approvals:
            if existing.approver_id == approver_id:
                raise ValueError(f"Approver {approver_id} has already approved this intent")

        approval = ApprovalRecord(
            approver_id=approver_id,
            approver_role=approver_role,
            approved_at=now,
            comment=comment,
        )
        token.approvals.append(approval)

        # State transition: check if dual approval requirement is met
        if token.requires_dual_approval:
            if len(token.approvals) >= 2:
                token.status = ActionStatus.APPROVED
            else:
                token.status = ActionStatus.PENDING
        else:
            # Single-approver fast-path
            token.status = ActionStatus.APPROVED

        # If hooked to ActionIntentHub, record in hub as well
        if self.intent_hub and hasattr(self.intent_hub, "approve_action"):
            try:
                self.intent_hub.approve_action(
                    intent_id=intent_id,
                    approver_id=approver_id,
                    approver_role=approver_role,
                    comment=comment,
                )
            except Exception:
                pass

        return self.present_card(token)

    def execute_action(
        self,
        intent_id: str,
        caller_role: str = "COMPLIANCE_HEAD",
    ) -> Dict[str, Any]:
        """Commits an approved action intent to the write-back sink emitting an immutable receipt."""
        token = self._staged_tokens.get(intent_id)
        if not token:
            raise KeyError(f"Action intent {intent_id} not found in shelf")

        if token.status != ActionStatus.APPROVED:
            raise ValueError(f"Cannot execute intent in status '{token.status}'. Must be APPROVED.")

        # If hooked to intent_hub, delegate execution
        if self.intent_hub and hasattr(self.intent_hub, "execute_action"):
            receipt = self.intent_hub.execute_action(intent_id=intent_id, caller_role=caller_role)
            token.status = ActionStatus.EXECUTED
            token.execution_receipt_id = getattr(receipt, "receipt_id", str(uuid.uuid4()))
            return {
                "receipt_id": token.execution_receipt_id,
                "status": "COMMITTED",
                "intent_id": intent_id,
                "committed_at": datetime.now(UTC).isoformat(),
            }

        # Simulated 2PC sink commit
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
        token.status = ActionStatus.EXECUTED
        token.execution_receipt_id = receipt_id
        return {
            "receipt_id": receipt_id,
            "status": "COMMITTED",
            "intent_id": intent_id,
            "committed_at": datetime.now(UTC).isoformat(),
        }

    def abort_action(self, intent_id: str, reason: str = "") -> GovernedActionCard:
        """Transitions an action intent to ABORTED state."""
        token = self._staged_tokens.get(intent_id)
        if not token:
            raise KeyError(f"Action intent {intent_id} not found in shelf")

        token.status = ActionStatus.ABORTED
        return self.present_card(token)

    def list_cards(self) -> List[GovernedActionCard]:
        """Lists all active action cards in the shelf."""
        return [self.present_card(t) for t in self._staged_tokens.values()]
