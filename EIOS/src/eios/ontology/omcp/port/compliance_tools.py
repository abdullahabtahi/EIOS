"""Compliance capabilities (spec 023): read and explain the decision trail; the agent never writes to it."""

from pydantic import Field

from eios.common.validation import StrictModel
from eios.ontology.config import SecurityMarking
from eios.ontology.omcp.port.common import envelope
from eios.ontology.omcp.port.contracts import DataOrigin, PortError, ToolErrorCode, ToolResult
from eios.ontology.omcp.port.principal import Principal, Workstation
from eios.ontology.omcp.port.readmodels import ReadModels
from eios.ontology.omcp.port.registry import Handler, ToolSpec

AUDITOR = (Workstation.COMPLIANCE_AUDITOR,)
MARK = (SecurityMarking.SENSITIVE_COMPLIANCE,)
_SVC = "cockpit.compliance.ComplianceExplorerService"


class NoArgs(StrictModel):
    pass


class LedgerArgs(StrictModel):
    start_seq: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=50)


class IntentArgs(StrictModel):
    intent_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")


def _origin(ctx: ReadModels) -> DataOrigin:
    return DataOrigin.LIVE if ctx.compliance.sequencer is not None else DataOrigin.FIXTURE


# --- get_ledger_timeline ---------------------------------------------------------------------------------


class LedgerEntry(StrictModel):
    ledger_seq: int
    event_type: str
    actor_ref: str
    timestamp: str
    is_worm_anchored: bool


class LedgerTimeline(ToolResult):
    entries: list[LedgerEntry]


def get_ledger_timeline(ctx: ReadModels, _who: Principal, args: LedgerArgs) -> LedgerTimeline:
    rows = ctx.compliance.get_ledger_timeline(start_seq=args.start_seq, limit=args.limit)
    rows = [r for r in rows if r["ledger_seq"] >= args.start_seq][
        : args.limit
    ]  # the fixture path ignores both
    base = envelope(
        ctx,
        "compliance.ledger",
        None,
        f"{_SVC}.get_ledger_timeline",
        {"entries[].ledger_seq": "sequence"},
        MARK,
    )
    base["data_origin"] = _origin(ctx)
    return LedgerTimeline(
        **base,
        entries=[
            LedgerEntry(
                ledger_seq=r["ledger_seq"],
                event_type=r["event_type"],
                actor_ref=r["actor_id"],
                timestamp=r["timestamp"],
                is_worm_anchored=r["is_worm_anchored"],
            )
            for r in rows
        ],
    )


# --- get_intent_status -----------------------------------------------------------------------------------


class IntentStatus(ToolResult):
    intent_id: str
    action_type: str
    target_entity_id: str
    severity: str
    status: str
    first_approver_role: str
    second_approver_role: str
    execution_receipt_id: str | None


def get_intent_status(ctx: ReadModels, _who: Principal, args: IntentArgs) -> IntentStatus:
    log = ctx.compliance.get_four_eyes_approval_log()
    if args.intent_id is not None:
        log = [r for r in log if r["intent_id"] == args.intent_id]
    if not log:
        raise PortError(ToolErrorCode.NOT_FOUND, "no such intent")
    r = log[-1]  # the log is oldest first; no id means the latest
    return IntentStatus(
        **envelope(
            ctx,
            "compliance.intent_status",
            r["target_entity_id"],
            f"{_SVC}.get_four_eyes_approval_log",
            {},
            MARK,
        ),
        intent_id=r["intent_id"],
        action_type=r["action_type"],
        target_entity_id=r["target_entity_id"],
        severity=r["severity"],
        status=r["status"],
        first_approver_role=r["first_approver"]["role"],
        second_approver_role=r["second_approver"]["role"],
        execution_receipt_id=r["execution_receipt_id"],
    )


# --- get_audit_status ------------------------------------------------------------------------------------


class AuditStatus(ToolResult):
    checkpoint_id: str
    chain_head_seq: int
    retention_expiration: str
    compliance_lock_mode: str
    is_immutable: bool


def get_audit_status(ctx: ReadModels, _who: Principal, _args: NoArgs) -> AuditStatus:
    proofs = ctx.compliance.get_worm_compliance_proofs()
    if not proofs:
        raise PortError(ToolErrorCode.DATA_UNAVAILABLE, "no retention checkpoint exists yet")
    p = proofs[-1]
    base = envelope(
        ctx,
        "compliance.audit_status",
        None,
        f"{_SVC}.get_worm_compliance_proofs",
        {"chain_head_seq": "sequence"},
        MARK,
    )
    base["data_origin"] = (
        DataOrigin.LIVE if ctx.compliance.worm_service is not None else DataOrigin.FIXTURE
    )
    return AuditStatus(
        **base,
        checkpoint_id=p["checkpoint_id"],
        chain_head_seq=p["chain_head_seq"],
        retention_expiration=p["retention_expiration"],
        compliance_lock_mode=p["compliance_lock_mode"],
        is_immutable=p["is_immutable"],
    )


# --- verify_chain ----------------------------------------------------------------------------------------


class ChainVerification(ToolResult):
    is_chain_unbroken: bool
    is_simulated: bool
    total_entries_verified: int
    worm_anchors_matched: int
    chain_head_hash: str
    integrity_score_pct: float


def verify_chain(ctx: ReadModels, _who: Principal, _args: NoArgs) -> ChainVerification:
    r = ctx.compliance.verify_hash_chain_interactive()
    simulated = (
        ctx.compliance.audit_walker is None
    )  # without a ledger the service returns a canned pass
    base = envelope(
        ctx,
        "compliance.verify_chain",
        None,
        f"{_SVC}.verify_hash_chain_interactive",
        {
            "total_entries_verified": "entries",
            "worm_anchors_matched": "anchors",
            "integrity_score_pct": "percent",
        },
        MARK,
    )
    base["data_origin"] = DataOrigin.FIXTURE if simulated else DataOrigin.LIVE
    return ChainVerification(
        **base,
        is_chain_unbroken=r["is_chain_unbroken"],
        is_simulated=simulated,
        total_entries_verified=r["total_entries_verified"],
        worm_anchors_matched=r["worm_anchors_matched"],
        chain_head_hash=r["chain_head_hash"],
        integrity_score_pct=r["integrity_score_pct"],
    )


def _spec(
    name: str, cap: str, args: type[StrictModel], out: type[ToolResult], fn: Handler
) -> ToolSpec:
    return ToolSpec(name, cap, "evidence", AUDITOR, args, out, fn, 300.0, MARK)


TOOLS: tuple[ToolSpec, ...] = (
    _spec(
        "get_ledger_timeline", "compliance.ledger", LedgerArgs, LedgerTimeline, get_ledger_timeline
    ),
    _spec(
        "get_intent_status", "compliance.intent_status", IntentArgs, IntentStatus, get_intent_status
    ),
    _spec("get_audit_status", "compliance.audit_status", NoArgs, AuditStatus, get_audit_status),
    _spec("verify_chain", "compliance.verify_chain", NoArgs, ChainVerification, verify_chain),
)
