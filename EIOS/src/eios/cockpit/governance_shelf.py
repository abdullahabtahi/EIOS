"""Governed Action Shelf Presenter and Two-Phase Commit State Machine Coordinator.

Strict institutional light mode COP invariants and Principle II / IV governed 2PC commitments.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from eios.cockpit.schemas import validate_contract
from eios.ontology.actions.intent_hub import TokenExpiredError
from eios.ontology.actions.models import (
    ActionIntentToken,
    ActionStatus,
    ApprovalRecord,
)
from eios.ontology.actions.record_store import ModelStore, RecordStore, default_record_store
from eios.ontology.actions.signer import ActionSigner

_LOG = logging.getLogger("eios.cockpit.governance_shelf")

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
    first_approver_id: str | None = None
    second_approver_id: str | None = None
    kms_signature_verified: bool
    status: str
    seconds_remaining: int

    def to_contract_dict(self) -> dict[str, Any]:
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
    """Presents staged 2PC action cards with Four-Eyes dual approval.

    With an ``intent_hub`` the shelf is a view over the hub's durable, ledgered state: approvals,
    execution and aborts go through the hub and its errors propagate. Without one (unit tests,
    isolated demos) it keeps its own token store. In both modes a card's ``kms_signature_verified``
    is the result of verifying the token's signature with ``signer``; with no signer it is False.
    """

    FAST_PATH_BUDGET_THRESHOLD: float = 2500.0

    def __init__(
        self,
        intent_hub: Any | None = None,
        signer: ActionSigner | None = None,
        token_records: RecordStore | None = None,
    ) -> None:
        self.intent_hub = intent_hub
        self.signer = signer or getattr(intent_hub, "signer", None)
        self._tokens: ModelStore[ActionIntentToken] | None = (
            None
            if intent_hub is not None
            else ModelStore(
                token_records or default_record_store("shelf_tokens"), ActionIntentToken
            )
        )

    @property
    def _local_tokens(self) -> ModelStore[ActionIntentToken]:
        if self._tokens is None:
            raise RuntimeError("the shelf delegates to the intent hub")
        return self._tokens

    # ---- state access -------------------------------------------------------------------------
    def stage_token(self, token: ActionIntentToken) -> GovernedActionCard:
        """Stage an externally built token (standalone mode only; hub mode proposes through the hub)."""
        if self._tokens is None:
            raise ValueError("In hub mode tokens must be proposed through the intent hub")
        self._local_tokens.put(token.intent_id, token)
        return self.present_card(token)

    def get_token(self, intent_id: str) -> ActionIntentToken | None:
        if self.intent_hub is not None:
            found: ActionIntentToken | None = self.intent_hub.find(intent_id)
            return found
        return self._local_tokens.get(intent_id)

    def _require(self, intent_id: str) -> ActionIntentToken:
        token = self.get_token(intent_id)
        if token is None:
            raise KeyError(f"Action intent {intent_id} not found in shelf")
        return token

    def _all_tokens(self) -> list[ActionIntentToken]:
        if self.intent_hub is not None:
            tokens: list[ActionIntentToken] = self.intent_hub.list_tokens()
            return tokens
        return sorted(self._local_tokens.list(), key=lambda t: t.issued_at)

    def _signature_verified(self, token: ActionIntentToken) -> bool:
        if self.signer is None or not token.signature:
            return False
        try:
            return bool(self.signer.verify_token(token))
        except Exception:
            _LOG.warning(
                "signature verification raised for intent %s", token.intent_id, exc_info=True
            )
            return False

    # ---- presentation -------------------------------------------------------------------------
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
            kms_signature_verified=self._signature_verified(token),
            status=card_status,
            seconds_remaining=remaining,
        )

    def get_approval_modal_context(
        self,
        intent_id: str,
        officer_id: str,
        officer_role: str,
    ) -> dict[str, Any]:
        """Provides full contextual state and eligibility checks for the Four-Eyes approval modal."""
        token = self._require(intent_id)

        card = self.present_card(token)
        now = datetime.now(UTC)
        is_expired = token.expires_at <= now or card.status == "EXPIRED"

        # Check eligibility: officer cannot sign twice
        has_already_signed = any(a.approver_id == officer_id for a in token.approvals)
        can_approve = (
            not is_expired and not has_already_signed and card.status in ["PENDING_APPROVAL"]
        )

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
        """Record a human sign-off. In hub mode the hub enforces four-eyes and ledgers the approval."""
        if self.intent_hub is not None:
            try:
                token = self.intent_hub.approve_action(
                    intent_id=intent_id,
                    approver_id=approver_id,
                    role=approver_role,
                    comment=comment,
                )
            except TokenExpiredError:
                return self.present_card(self._require(intent_id))
            return self.present_card(token)
        now = datetime.now(UTC)

        def approve(token: ActionIntentToken) -> ActionIntentToken:
            if token.expires_at <= now:
                return token.model_copy(update={"status": ActionStatus.EXPIRED})
            if any(existing.approver_id == approver_id for existing in token.approvals):
                raise ValueError(f"Approver {approver_id} has already approved this intent")
            approvals = [
                *token.approvals,
                ApprovalRecord(
                    approver_id=approver_id,
                    approver_role=approver_role,
                    approved_at=now,
                    comment=comment,
                ),
            ]
            fully_approved = not token.requires_dual_approval or len(approvals) >= 2
            status = ActionStatus.APPROVED if fully_approved else ActionStatus.PENDING
            return token.model_copy(update={"approvals": approvals, "status": status})

        self._require(intent_id)
        return self.present_card(self._local_tokens.update(intent_id, approve))

    def execute_action(
        self,
        intent_id: str,
        caller_role: str = "COMPLIANCE_HEAD",
    ) -> dict[str, Any]:
        """Commit an approved intent to the write-back sink and return its receipt."""
        token = self._require(intent_id)
        if token.status != ActionStatus.APPROVED:
            raise ValueError(f"Cannot execute intent in status '{token.status}'. Must be APPROVED.")

        if self.intent_hub is not None:
            result = self.intent_hub.execute_action(intent_id=intent_id)
            receipt_id = getattr(result, "receipt_id", None) or getattr(
                result, "execution_receipt_id", None
            )
            return {
                "receipt_id": receipt_id,
                "status": "COMMITTED",
                "intent_id": intent_id,
                "committed_at": datetime.now(UTC).isoformat(),
            }
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}"
        self._local_tokens.update(
            intent_id,
            lambda t: t.model_copy(
                update={"status": ActionStatus.EXECUTED, "execution_receipt_id": receipt_id}
            ),
        )
        return {
            "receipt_id": receipt_id,
            "status": "COMMITTED",
            "intent_id": intent_id,
            "committed_at": datetime.now(UTC).isoformat(),
        }

    def abort_action(self, intent_id: str, reason: str = "") -> GovernedActionCard:
        """Abort an intent."""
        if self.intent_hub is not None:
            return self.present_card(self.intent_hub.abort_action(intent_id, reason))
        self._require(intent_id)
        return self.present_card(
            self._local_tokens.update(
                intent_id, lambda t: t.model_copy(update={"status": ActionStatus.ABORTED})
            )
        )

    def list_cards(self) -> list[GovernedActionCard]:
        """Lists all action cards in the shelf, oldest first."""
        return [self.present_card(t) for t in self._all_tokens()]
