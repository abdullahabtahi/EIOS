"""The compliance views over the real decision ledger: entries, signed checkpoints and four-eyes records (spec 032).

Every row here is read from the governance runtime the action shelf writes to, so a hold staged and approved on
the shelf appears in the timeline, the approval log and the assistant's answers. An empty ledger reads as empty;
nothing is filled in.
"""

from __future__ import annotations

from typing import Any

from eios.ontology.actions.intent_hub import ActionIntentHub
from eios.ontology.actions.models import ActionIntentToken, ApprovalRecord, LedgerEntry
from eios.ontology.actions.sequencer import LedgerSequencer
from eios.ontology.actions.worm import WORMAnchorService

SIGNED_CHECKPOINT = (
    "SIGNED_CHECKPOINT"  # app-level signed anchor; no bucket retention lock is claimed
)
_TARGET_KEYS = ("entity_id", "partner_id", "client_id", "account_id", "case_id", "txn_id")
_ACTOR_KEYS = ("approver_id", "rejected_by")


def _target(parameters: dict[str, Any]) -> str:
    return next((str(parameters[k]) for k in _TARGET_KEYS if parameters.get(k)), "")


def _actor(entry: LedgerEntry, tokens: dict[str, ActionIntentToken]) -> str:
    found = next((str(entry.payload[k]) for k in _ACTOR_KEYS if entry.payload.get(k)), "")
    if found:
        return found
    token = tokens.get(entry.entity_id)
    return token.requester_agent_id if token else "system"


def _tokens(hub: ActionIntentHub | None) -> dict[str, ActionIntentToken]:
    return {t.intent_id: t for t in hub.list_tokens()} if hub else {}


def ledger_timeline(
    sequencer: LedgerSequencer,
    worm: WORMAnchorService | None,
    hub: ActionIntentHub | None,
    start_seq: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Ledger entries from `start_seq`, oldest first; an entry is anchored once a checkpoint covers it."""
    anchored_to = max((c.chain_head_seq for c in worm.get_checkpoints()), default=0) if worm else 0
    tokens = _tokens(hub)
    rows = [e for e in sequencer.entries if e.ledger_seq >= start_seq][:limit]
    return [
        {
            "ledger_seq": e.ledger_seq,
            "event_type": e.event_type.value,
            "entity_id": e.entity_id,
            "prev_hash": e.prev_hash,
            "current_hash": e.current_hash,
            "actor_id": _actor(e, tokens),
            "timestamp": e.recorded_at.isoformat(),
            "is_worm_anchored": e.ledger_seq <= anchored_to,
        }
        for e in rows
    ]


def checkpoint_proofs(worm: WORMAnchorService) -> list[dict[str, Any]]:
    """Signed chain-head checkpoints, oldest first."""
    return [
        {
            "checkpoint_id": f"CKPT-{c.checkpoint_seq:06d}",
            "chain_head_seq": c.chain_head_seq,
            "root_hash": c.chain_head_hash,
            "locked_at": c.locked_at.isoformat(),
            "retention_expiration": c.retention_until.isoformat(),
            "compliance_lock_mode": SIGNED_CHECKPOINT,
            "is_immutable": c.compliance_mode,
        }
        for c in worm.get_checkpoints()
    ]


def _approver(record: ApprovalRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {
        "officer_id": record.approver_id,
        "role": record.approver_role,
        "approved_at": record.approved_at.isoformat(),
        "comment": record.comment,
    }


def approval_log(hub: ActionIntentHub) -> list[dict[str, Any]]:
    """Every intent the hub holds with its sign-offs so far, oldest first; a pending intent has none."""
    out: list[dict[str, Any]] = []
    for t in hub.list_tokens():
        first = t.approvals[0] if t.approvals else None
        second = t.approvals[1] if len(t.approvals) > 1 else None
        out.append(
            {
                "intent_id": t.intent_id,
                "action_type": t.action_type,
                "target_entity_id": _target(t.parameters),
                "severity": t.severity.value,
                "first_approver": _approver(first),
                "second_approver": _approver(second),
                "requires_dual_approval": t.requires_dual_approval,
                "execution_receipt_id": t.execution_receipt_id,
                "status": t.status.value,
            }
        )
    return out
