"""The compliance workstation payload, read from the decision ledger the shelf writes to (spec 032).

Counts and hashes come from the ledger, the signed checkpoints and the audit walk. A ledger with no checkpoint says
so; nothing claims a storage retention lock the platform does not hold.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from eios.cockpit.aml_metric import metric
from eios.cockpit.compliance import ComplianceExplorerService
from eios.ontology.actions.models import ActionIntentToken

TIMELINE_LIMIT = 50
_ENGINE = "ContinuousAuditWalker"


def ledger_payload(
    svc: ComplianceExplorerService,
    list_tokens: Callable[[], Sequence[ActionIntentToken]] | None = None,
) -> dict[str, Any]:
    """Entries newest first, every intent's sign-offs, the checkpoints and a fresh audit walk."""
    read = svc.read_ledger(list_tokens)  # one listing of each collection for the whole request
    return {
        "entries": list(reversed(svc.get_ledger_timeline(start_seq=1, limit=10_000, read=read)))[
            :TIMELINE_LIMIT
        ],
        "approvals": list(reversed(svc.get_four_eyes_approval_log(read))),
        "checkpoints": svc.get_worm_compliance_proofs(read),
        "verification": svc.verify_hash_chain_interactive(read),
        "is_simulated": svc.sequencer is None,
    }


def _triage(entries: list[dict[str, Any]], now_iso: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"item_seq_{e['ledger_seq']}",
            "title": f"Ledger #{e['ledger_seq']} {e['event_type'].replace('_', ' ').lower()}",
            "subtitle": f"{e['actor_id']} | {e['current_hash'][:12]}",
            "entity_id": f"SEQ-{e['ledger_seq']}",
            "priority_score": 0.5,
            "severity": "INFO",
            "status": "RESOLVED",
            "timestamp": e.get("timestamp", now_iso),
        }
        for e in entries
    ]


def _retention_days(proof: dict[str, Any] | None, now_iso: str) -> int | None:
    if proof is None:
        return None
    until = datetime.fromisoformat(proof["retention_expiration"])
    return max((until - datetime.fromisoformat(now_iso)).days, 0)


def _summary(payload: dict[str, Any]) -> str:
    v = payload["verification"]
    total = v["total_entries_verified"]
    if total == 0:
        return "The decision ledger is empty: no action has been staged yet."
    state = "unbroken" if v["is_chain_unbroken"] else "broken"
    return f"Hash chain {state} across {total} ledger entries."


def _checkpoint_section(proof: dict[str, Any] | None, now_iso: str) -> dict[str, Any]:
    days = _retention_days(proof, now_iso)
    if proof is None or days is None:
        return {
            "section_id": "sec_checkpoint",
            "title": "Signed checkpoint",
            "narrative_text": "No signed checkpoint has been taken yet.",
            "citations": [],
            "metrics": [],
        }
    return {
        "section_id": "sec_checkpoint",
        "title": "Signed checkpoint",
        "narrative_text": (
            f"Checkpoint {proof['checkpoint_id']} anchors the chain head at entry "
            f"{proof['chain_head_seq']}; its retention runs to {proof['retention_expiration'][:10]}."
        ),
        "citations": ["worm_checkpoint_id"],
        "metrics": [
            metric(
                "worm_retention_days", f"{days:,} days", float(days), now_iso, engine_name=_ENGINE
            )
        ],
    }


def workstation(
    svc: ComplianceExplorerService,
    now_iso: str,
    list_tokens: Callable[[], Sequence[ActionIntentToken]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Triage items, dossier and canvas for the compliance auditor."""
    payload = ledger_payload(svc, list_tokens)
    proof = payload["checkpoints"][-1] if payload["checkpoints"] else None
    dossier = {
        "dossier_id": "dos_compliance_timeline",
        "entity_id": "LEDGER",
        "headline": "Decision ledger and audit trail",
        "executive_summary": _summary(payload),
        "sections": [_checkpoint_section(proof, now_iso)],
        "as_of_timestamp": now_iso,
        "is_cached_snapshot": False,
    }
    canvas = {
        "canvas_type": "LEDGER_TIMELINE",
        "payload": {
            "timeline": payload["entries"],
            "worm_proof": proof,
            "chain_valid": payload["verification"]["is_chain_unbroken"],
        },
    }
    return _triage(payload["entries"], now_iso), dossier, canvas
