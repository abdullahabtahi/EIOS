"""Governed Action Intent Hub and Four-Eyes Approval State Machine (Principle II, US6, US2)."""

import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from eios.ingestion.hot_state import HotStateEngine
from eios.ontology.actions.models import (
    ActionIntentToken,
    ActionSeverity,
    ActionStatus,
    ApprovalRecord,
    ExecutionReceipt,
    LedgerEventType,
)
from eios.ontology.actions.record_store import ModelStore, RecordStore, default_record_store
from eios.ontology.actions.signer import ActionSigner, default_action_signer

APPROVAL_ATTEMPTS = 8


class InvalidActionParameterError(Exception):
    pass


class ConcurrentModificationError(Exception):
    """The stored token changed since it was read; reload and retry."""


class NonceReplayError(Exception):
    pass


class TokenExpiredError(Exception):
    pass


class FourEyesApprovalRequiredError(Exception):
    pass


class FourEyesViolationError(Exception):
    """The proposer of an intent tried to approve it (Principle II)."""


class ActionExecutionError(Exception):
    pass


CANONICAL_ACTION_SPECS = {
    "FreezeAccount": {
        "required_params": ["client_id", "reason_code"],
        "severity": ActionSeverity.HIGH,
    },
    "HoldWithdrawal": {
        "required_params": ["txn_id", "reason"],
        "severity": ActionSeverity.HIGH,
    },
    "ClawbackCommission": {
        "required_params": ["partner_id", "period", "amount"],
        "severity": ActionSeverity.HIGH,
    },
    "SuspendPartner": {
        "required_params": ["partner_id", "scope"],
        "severity": ActionSeverity.HIGH,
    },
    "LaunchRetentionPlaybook": {
        "required_params": ["partner_ids", "playbook_id", "budget"],
        "severity": ActionSeverity.MEDIUM,
    },
    "EscalateToMLRO": {
        "required_params": ["case_id", "summary_ref"],
        "severity": ActionSeverity.MEDIUM,
    },
    "FileSARDraft": {
        "required_params": ["case_id", "template_id"],
        "severity": ActionSeverity.MEDIUM,
    },
    "AdjustPartnerTier": {
        "required_params": ["partner_id", "target_tier"],
        "severity": ActionSeverity.MEDIUM,
    },
    "ReviewSpreadPricing": {
        "required_params": ["symbol", "target_spread_pips"],
        "severity": ActionSeverity.LOW,
    },
    "LaunchRetentionCampaign": {
        "required_params": ["partner_id", "tier"],
        "severity": ActionSeverity.MEDIUM,
    },
    # Partner-retention and AML actions the cockpit stages (added with the cockpit contract enum).
    "DeployRetentionConcession": {
        "required_params": ["partner_id"],
        "severity": ActionSeverity.MEDIUM,
    },
    "WhitelistDirectCashierRail": {
        "required_params": ["partner_id"],
        "severity": ActionSeverity.MEDIUM,
    },
    "AllocateCoMarketingBudget": {
        "required_params": ["partner_id"],
        "severity": ActionSeverity.MEDIUM,
    },
    "SuppressCGNATProxyCluster": {
        "required_params": ["entity_id"],
        "severity": ActionSeverity.MEDIUM,
    },
}


class _TokenBook:
    """Token records with optimistic concurrency. Reads return independent copies, so a change
    only takes effect through ``save``, which rejects a stale revision."""

    def __init__(self, records: RecordStore) -> None:
        self._records = records
        self._models = ModelStore(records, ActionIntentToken)

    def __contains__(self, intent_id: str) -> bool:
        return self._records.get(intent_id) is not None

    def __getitem__(self, intent_id: str) -> ActionIntentToken:
        token = self._models.get(intent_id)
        if token is None:
            raise KeyError(intent_id)
        return token

    def create(self, token: ActionIntentToken) -> None:
        if not self._models.create(token.intent_id, token):
            raise ConcurrentModificationError(f"intent '{token.intent_id}' already exists")

    def save(self, token: ActionIntentToken) -> None:
        expected = token.revision

        def mutate(current: dict[str, Any]) -> dict[str, Any]:
            if current.get("revision", 0) != expected:
                raise ConcurrentModificationError(
                    f"intent '{token.intent_id}' was modified concurrently"
                )
            return {**token.model_dump(mode="json"), "revision": expected + 1}

        self._records.update(token.intent_id, mutate)
        token.revision = expected + 1

    def attach_ledger_seq(self, intent_id: str, seq: int) -> None:
        """Record the ledger sequence without a revision check; it never conflicts with approvals."""
        self._records.update(intent_id, lambda current: {**current, "ledger_seq": seq})

    def items(self) -> list[tuple[str, ActionIntentToken]]:
        return [(t.intent_id, t) for t in self._models.list()]


class ActionIntentHub:
    """Non-autonomous Action Intent Hub generating KMS-signed mutation proposals."""

    FAST_PATH_BUDGET_THRESHOLD: float = 2500.0

    def __init__(
        self,
        signer: ActionSigner | None = None,
        sequencer: Any | None = None,
        sink: Any | None = None,
        hot_state_engine: HotStateEngine | None = None,
        outcomes_store: Any | None = None,
        token_records: RecordStore | None = None,
        nonce_records: RecordStore | None = None,
    ) -> None:
        self.signer = signer or default_action_signer()
        self.sequencer = sequencer
        self.sink = sink
        self.hot_state = hot_state_engine
        self.outcomes_store = outcomes_store
        self._token_store: RecordStore = token_records or default_record_store("intent_tokens")
        self._tokens = _TokenBook(self._token_store)
        self._nonces: RecordStore = nonce_records or default_record_store("intent_nonces")

    def _register_nonce(self, nonce: str) -> None:
        if not self._nonces.create(nonce, {"registered_at": datetime.now(UTC).isoformat()}):
            raise NonceReplayError(f"Action intent nonce '{nonce}' has already been used.")

    def _persist_token(self, token: ActionIntentToken) -> None:
        """Save the token (revision-checked) and mirror it to DuckDB hot state if configured."""
        self._tokens.save(token)
        self._mirror_to_hot_state(token)

    def _mirror_to_hot_state(self, token: ActionIntentToken) -> None:
        """Mirror token state to DuckDB hot state if configured."""
        if not self.hot_state:
            return
        cursor = self.hot_state.get_cursor()
        cursor.execute("DELETE FROM governed_action_intents WHERE intent_id = ?", [token.intent_id])
        cursor.execute(
            """
            INSERT INTO governed_action_intents (
                intent_id, action_type, parameters, evidence_refs, severity,
                status, nonce, issued_at, expires_at, requester_agent_id,
                kms_key_id, signature, approvals, propensity_score,
                causal_context, requires_dual_approval, policy_tags,
                ledger_seq, execution_receipt_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                token.intent_id,
                token.action_type,
                json.dumps(token.parameters),
                json.dumps(token.evidence_refs),
                token.severity.value if hasattr(token.severity, "value") else str(token.severity),
                token.status.value if hasattr(token.status, "value") else str(token.status),
                token.nonce,
                token.issued_at,
                token.expires_at,
                token.requester_agent_id,
                token.kms_key_id,
                token.signature,
                json.dumps([a.model_dump(mode="json") for a in token.approvals]),
                token.propensity_score,
                json.dumps(token.causal_context),
                token.requires_dual_approval,
                json.dumps(token.policy_tags),
                token.ledger_seq,
                token.execution_receipt_id,
            ],
        )

    def propose_action(
        self,
        action_type: str,
        parameters: dict[str, Any],
        evidence_refs: list[str],
        requester_agent_id: str = "DomainAgent",
        propensity_score: float | None = 1.0,
        causal_context: dict[str, Any] | None = None,
        policy_tags: list[str] | None = None,
        require_dual_approval: bool = False,
    ) -> ActionIntentToken:
        """Propose an operational action intent. Emits signed ActionIntentToken."""
        if action_type not in CANONICAL_ACTION_SPECS:
            raise InvalidActionParameterError(f"Unknown Action Type '{action_type}'.")

        spec = CANONICAL_ACTION_SPECS[action_type]
        for req in spec["required_params"]:
            if req not in parameters:
                raise InvalidActionParameterError(
                    f"Action '{action_type}' missing required parameter '{req}'."
                )

        intent_id = str(uuid.uuid4())
        nonce = secrets.token_hex(16)
        self._register_nonce(nonce)

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=15)

        # Evaluate dual-approval requirement: HIGH severity always requires 2 approvers.
        # MEDIUM severity requires 2 approvers if budget exceeds threshold, else single approver fast-path.
        financial_impact = float(parameters.get("budget", parameters.get("amount", 0.0)) or 0.0)
        if spec["severity"] == ActionSeverity.HIGH:
            requires_dual = True
        elif spec["severity"] == ActionSeverity.MEDIUM:
            requires_dual = financial_impact > self.FAST_PATH_BUDGET_THRESHOLD
        else:
            requires_dual = False

        # A caller may raise the approval bar above policy, never lower it.
        requires_dual = requires_dual or require_dual_approval

        signing_payload = {
            "intent_id": intent_id,
            "action_type": action_type,
            "parameters": parameters,
            "evidence_refs": evidence_refs,
            "severity": spec["severity"].value,
            "nonce": nonce,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "requester_agent_id": requester_agent_id,
        }
        if propensity_score is not None:
            signing_payload["propensity_score"] = propensity_score
        if causal_context:
            signing_payload["causal_context"] = causal_context

        sig_b64 = self.signer.sign_payload(signing_payload)

        token = ActionIntentToken(
            intent_id=intent_id,
            action_type=action_type,
            parameters=parameters,
            evidence_refs=evidence_refs,
            severity=spec["severity"],
            status=ActionStatus.PENDING,
            nonce=nonce,
            issued_at=now,
            expires_at=expires_at,
            requester_agent_id=requester_agent_id,
            kms_key_id=self.signer.key_id,
            signature=sig_b64,
            propensity_score=propensity_score,
            causal_context=causal_context or {},
            requires_dual_approval=requires_dual,
            policy_tags=[
                "FAST_PATH_ELIGIBLE" if not requires_dual else "DUAL_APPROVAL_MANDATORY",
                *(policy_tags or []),
            ],
        )

        if self.sequencer:
            entry = self.sequencer.record_event(
                event_type=LedgerEventType.PROPOSAL_CREATED,
                entity_id=token.intent_id,
                payload={
                    "intent_id": token.intent_id,
                    "action_type": token.action_type,
                    "parameters": token.parameters,
                    "severity": token.severity.value,
                    "requires_dual_approval": token.requires_dual_approval,
                    "nonce": token.nonce,
                    "status": token.status.value,
                },
            )
            token.ledger_seq = entry.ledger_seq

        if self.outcomes_store:
            entity_id = (
                parameters.get("partner_id")
                or parameters.get("client_id")
                or (
                    parameters.get("partner_ids", [None])[0]
                    if isinstance(parameters.get("partner_ids"), list)
                    and parameters.get("partner_ids")
                    else None
                )
                or parameters.get("txn_id")
                or "UNKNOWN"
            )
            self.outcomes_store.record_decision(
                intent_id=token.intent_id,
                entity_id=entity_id,
                action_type=token.action_type,
                treatment_assigned=1,
                propensity_score=token.propensity_score or 1.0,
                causal_features=token.causal_context,
                manager_override_flag=False,
                override_reason=None,
            )

        self._tokens.create(token)
        self._mirror_to_hot_state(token)
        return token

    def approve_action(
        self,
        intent_id: str,
        approver_id: str,
        role: str,
        comment: str = "",
        override_applied: bool = False,
        override_reason: str | None = None,
    ) -> ActionIntentToken:
        """Approve a pending action intent. Enforces dual approval when required.

        The approval is saved first with a revision check (retrying on a concurrent change), then
        sequenced into the ledger.
        """
        for _ in range(APPROVAL_ATTEMPTS):
            if intent_id not in self._tokens:
                raise KeyError(f"Intent '{intent_id}' not found.")
            token = self._tokens[intent_id]
            now = datetime.now(UTC)
            if now > token.expires_at:
                token.status = ActionStatus.EXPIRED
                self._persist_token(token)
                raise TokenExpiredError(f"Action intent '{intent_id}' has expired.")
            # Prevent duplicate approval by same person
            if approver_id == token.requester_agent_id:
                raise FourEyesViolationError(
                    f"Four-Eyes Violation: '{approver_id}' proposed intent '{intent_id}' and cannot approve it."
                )
            if any(a.approver_id == approver_id for a in token.approvals):
                raise InvalidActionParameterError(
                    f"Approver '{approver_id}' has already approved this intent."
                )
            token.approvals.append(
                ApprovalRecord(
                    approver_id=approver_id,
                    approver_role=role,
                    comment=comment,
                    override_applied=override_applied,
                    override_reason=override_reason,
                )
            )
            if token.requires_dual_approval:
                token.status = (
                    ActionStatus.APPROVED if len(token.approvals) >= 2 else ActionStatus.PENDING
                )
            else:
                token.status = ActionStatus.APPROVED
            try:
                self._persist_token(token)
            except ConcurrentModificationError:
                continue
            break
        else:
            raise ConcurrentModificationError(
                f"Approval of '{intent_id}' kept conflicting; retry the request."
            )

        if self.sequencer:
            entry = self.sequencer.record_event(
                event_type=LedgerEventType.APPROVAL_RECORDED,
                entity_id=token.intent_id,
                payload={
                    "intent_id": token.intent_id,
                    "approver_id": approver_id,
                    "role": role,
                    "comment": comment,
                    "override_applied": override_applied,
                    "resulting_status": token.status.value,
                    "total_approvals": len(token.approvals),
                },
            )
            self._tokens.attach_ledger_seq(token.intent_id, entry.ledger_seq)
            token.ledger_seq = entry.ledger_seq
        if override_applied and self.outcomes_store:
            self.outcomes_store.update_override(token.intent_id, override_reason=override_reason)
        return token

    def reject_action(
        self,
        intent_id: str,
        approver_id: str,
        role: str,
        reason: str = "",
    ) -> ActionIntentToken:
        """Reject a pending action intent."""
        if intent_id not in self._tokens:
            raise KeyError(f"Intent '{intent_id}' not found.")

        token = self._tokens[intent_id]
        token.status = ActionStatus.REJECTED

        if self.sequencer:
            entry = self.sequencer.record_event(
                event_type=LedgerEventType.ACTION_REJECTED,
                entity_id=token.intent_id,
                payload={
                    "intent_id": token.intent_id,
                    "rejected_by": approver_id,
                    "role": role,
                    "reason": reason,
                },
            )
            token.ledger_seq = entry.ledger_seq

        self._persist_token(token)
        return token

    def auto_stage_low_risk_actions(
        self,
        max_budget: float = 1000.0,
        system_role: str = "PolicyAutoStager",
    ) -> list[str]:
        """Automatically stages and approves eligible pending low-risk intents."""
        auto_approved = []
        for intent_id, token in list(self._tokens.items()):
            if token.status == ActionStatus.PENDING and not token.requires_dual_approval:
                financial_impact = float(
                    token.parameters.get("budget", token.parameters.get("amount", 0.0)) or 0.0
                )
                if financial_impact <= max_budget:
                    self.approve_action(
                        intent_id=intent_id,
                        approver_id="SYSTEM_POLICY_AGENT",
                        role=system_role,
                        comment=f"Auto-approved via policy threshold ($<= {max_budget})",
                    )
                    token.policy_tags.append("AUTO_STAGED")
                    auto_approved.append(intent_id)
        return auto_approved

    def execute_action(
        self,
        intent_id: str,
        idempotency_key: str | None = None,
    ) -> ActionIntentToken | ExecutionReceipt:
        """Simulate write-back execution. Strictly fails if not fully approved."""
        if intent_id not in self._tokens:
            raise KeyError(f"Intent '{intent_id}' not found.")

        token = self._tokens[intent_id]
        if token.status == ActionStatus.EXECUTED and self.sink is not None:
            idem_key = idempotency_key or f"IDEM-{token.intent_id}"
            if idem_key in self.sink._idempotency_cache:
                return self.sink._idempotency_cache[idem_key]

        if token.status != ActionStatus.APPROVED:
            if token.requires_dual_approval and len(token.approvals) < 2:
                raise FourEyesApprovalRequiredError(
                    f"Action '{intent_id}' requires dual approval (2 distinct approvers)."
                )
            raise ActionExecutionError(
                f"Action '{intent_id}' is not in APPROVED status (current: {token.status})."
            )

        if self.sink is not None:
            receipt = self.sink.commit_action(token, idempotency_key=idempotency_key)
            token.execution_receipt_id = receipt.receipt_id
            status_val = (
                receipt.status.value if hasattr(receipt.status, "value") else str(receipt.status)
            )
            if status_val == "COMMITTED":
                token.status = ActionStatus.EXECUTED
                ev_type = LedgerEventType.ACTION_EXECUTED
            else:
                token.status = ActionStatus.ABORTED
                ev_type = LedgerEventType.ACTION_ABORTED

            # Only record if sink did not already record to the same sequencer
            if self.sequencer and self.sink.sequencer != self.sequencer:
                entry = self.sequencer.record_event(
                    event_type=ev_type,
                    entity_id=token.intent_id,
                    payload={
                        "intent_id": token.intent_id,
                        "receipt_id": receipt.receipt_id,
                        "status": status_val,
                        "external_transaction_id": receipt.external_transaction_id,
                    },
                )
                token.ledger_seq = entry.ledger_seq
            elif self.sequencer:
                token.ledger_seq = self.sequencer.current_seq

            self._persist_token(token)
            return receipt

        else:
            token.status = ActionStatus.EXECUTED
            if self.sequencer:
                entry = self.sequencer.record_event(
                    event_type=LedgerEventType.ACTION_EXECUTED,
                    entity_id=token.intent_id,
                    payload={
                        "intent_id": token.intent_id,
                        "status": token.status.value,
                    },
                )
                token.ledger_seq = entry.ledger_seq

            self._persist_token(token)
            return token

    def find(self, intent_id: str) -> ActionIntentToken | None:
        """Return the token, or None when the intent does not exist."""
        return self._tokens[intent_id] if intent_id in self._tokens else None

    def list_tokens(self) -> list[ActionIntentToken]:
        """All tokens, oldest first."""
        return sorted((t for _, t in self._tokens.items()), key=lambda t: t.issued_at)

    def abort_action(self, intent_id: str, reason: str = "") -> ActionIntentToken:
        """Abort an intent that has not executed, recording the abort in the ledger."""
        for _ in range(APPROVAL_ATTEMPTS):
            token = self.get_status(intent_id)
            if token.status == ActionStatus.EXECUTED:
                raise ActionExecutionError(
                    f"Action '{intent_id}' already executed and cannot be aborted."
                )
            token.status = ActionStatus.ABORTED
            try:
                self._persist_token(token)
            except ConcurrentModificationError:
                continue
            break
        else:
            raise ConcurrentModificationError(
                f"Abort of '{intent_id}' kept conflicting; retry the request."
            )
        if self.sequencer:
            entry = self.sequencer.record_event(
                event_type=LedgerEventType.ACTION_ABORTED,
                entity_id=token.intent_id,
                payload={"intent_id": token.intent_id, "reason": reason},
            )
            self._tokens.attach_ledger_seq(token.intent_id, entry.ledger_seq)
            token.ledger_seq = entry.ledger_seq
        return token

    def get_status(self, intent_id: str) -> ActionIntentToken:
        """Retrieve current intent token state."""
        if intent_id not in self._tokens:
            raise KeyError(f"Intent '{intent_id}' not found.")
        return self._tokens[intent_id]
