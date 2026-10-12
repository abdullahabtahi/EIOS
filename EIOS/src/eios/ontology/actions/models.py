"""Domain Schemas for Governed Actions & Cryptographic Ledger (Slice S5 / F10)."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ActionSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ActionStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    ABORTED = "ABORTED"
    EXPIRED = "EXPIRED"


class ApprovalRecord(BaseModel):
    """Captures an authenticated human sign-off on an action intent."""

    approver_id: str = Field(description="Authenticated officer identity (from IdP claims)")
    approver_role: str = Field(description="Authorized role (e.g. MLRO, COMPLIANCE_HEAD, PARTNER_LEAD)")
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Approval timestamp")
    comment: str = Field(default="", description="Qualitative justification for review decision")
    override_applied: bool = Field(default=False, description="Whether approver modified budget/parameters")
    override_reason: str | None = Field(default=None, description="Documented reason if override applied")


class ActionIntentToken(BaseModel):
    """Governed Action Intent Token proposal signed with Cloud KMS ECDSA P-256."""

    intent_id: str = Field(description="Unique UUIDv4 identifying the action proposal")
    action_type: str = Field(description="Canonical action type from CANONICAL_ACTION_SPECS")
    parameters: dict[str, Any] = Field(description="Validated parameters matching action specification")
    evidence_refs: list[str] = Field(description="IDs of alerts, cases, or dossiers providing evidentiary proof")
    severity: ActionSeverity = Field(description="Risk severity level (LOW, MEDIUM, HIGH)")
    status: ActionStatus = Field(default=ActionStatus.PENDING, description="Current lifecycle state")
    nonce: str = Field(description="128-bit cryptographic single-use hex string")
    issued_at: datetime = Field(description="UTC timestamp of token issuance")
    expires_at: datetime = Field(description="UTC timestamp of token expiration (issued_at + 15 min)")
    requester_agent_id: str = Field(default="DomainAgent", description="Agent proposing the action")
    kms_key_id: str = Field(description="Cloud KMS Key resource ID used for asymmetric signing")
    signature: str = Field(description="Base64-encoded ASN.1 DER ECDSA P-256 signature")
    approvals: list[ApprovalRecord] = Field(default_factory=list, description="List of recorded human sign-offs")
    propensity_score: float | None = Field(default=1.0, ge=0.0, le=1.0, description="Estimated propensity score e(X)")
    causal_context: dict[str, Any] = Field(default_factory=dict, description="Contextual feature vector at proposal time")
    requires_dual_approval: bool = Field(default=True, description="Whether Four-Eyes authorization is mandatory")
    policy_tags: list[str] = Field(default_factory=list, description="Policy classification tags")
    ledger_seq: int | None = Field(default=None, description="Sequence number in atomic ledger once recorded")
    execution_receipt_id: str | None = Field(default=None, description="Linked receipt ID upon commit")


class LedgerEventType(StrEnum):
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    APPROVAL_RECORDED = "APPROVAL_RECORDED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_ABORTED = "ACTION_ABORTED"
    ACTION_REJECTED = "ACTION_REJECTED"
    COMPENSATION_RECORDED = "COMPENSATION_RECORDED"


class LedgerEntry(BaseModel):
    """Cryptographically chained atomic ledger record (ADR-017)."""

    ledger_seq: int = Field(ge=1, description="Strictly monotonic, 1-indexed sequence counter")
    prev_hash: str = Field(description="SHA-256 hex digest of predecessor, or genesis anchor")
    current_hash: str = Field(description="SHA-256 hex digest of prev_hash || ledger_seq || payload_digest")
    event_type: LedgerEventType = Field(description="Classification of lifecycle event")
    entity_id: str = Field(description="Identifier of primary entity (e.g. intent_id, receipt_id)")
    payload_digest: str = Field(description="SHA-256 hex digest of RFC 8785 canonical JSON payload")
    payload: dict[str, Any] = Field(description="Canonical event payload content")
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Commit timestamp")
    worm_checkpoint_seq: int | None = Field(default=None, description="Linked WORM checkpoint sequence, if locked")


class ExecutionStatus(StrEnum):
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    ABORTED = "ABORTED"


class ExecutionReceipt(BaseModel):
    """Emitted by SimulatedWriteBackSink upon committing an approved operational action."""

    receipt_id: str = Field(description="UUID identifying the execution receipt")
    intent_id: str = Field(description="Referenced ActionIntentToken intent_id")
    idempotency_key: str = Field(description="Unique idempotency deduplication key")
    external_transaction_id: str = Field(description="Simulated external core banking / payment reference ID")
    action_type: str = Field(description="Action executed")
    status: ExecutionStatus = Field(description="Final commit state")
    simulated_latency_ms: float = Field(default=15.0, ge=0.0, description="Simulated execution latency in milliseconds")
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Execution timestamp")
    side_effects: dict[str, Any] = Field(default_factory=dict, description="Simulated system mutations")
    compensation_intent_id: str | None = Field(default=None, description="Linked compensation intent if aborted")


class WORMAnchorCheckpoint(BaseModel):
    """Immutable WORM chain-head anchor checkpoint record simulating GCS Object Retention Compliance Mode."""

    checkpoint_seq: int = Field(ge=1, description="Strictly monotonic WORM checkpoint number")
    chain_head_seq: int = Field(ge=1, description="Highest ledger_seq locked at checkpoint creation")
    chain_head_hash: str = Field(description="SHA-256 hash digest of the chain head at checkpoint time")
    locked_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Lock creation timestamp")
    retention_until: datetime = Field(description="Immutable retention expiration timestamp (7 years)")
    compliance_mode: bool = Field(default=True, description="Strict compliance mode lock flag")
    lock_signature: str = Field(description="KMS signature verifying WORM anchor authenticity")


class DecisionOutcomeRecord(BaseModel):
    """Captures proposal propensity scores e(X), causal covariates, and forward multi-horizon actuals."""

    outcome_id: str = Field(description="Unique UUID identifying the outcome record")
    intent_id: str = Field(description="Referenced ActionIntentToken intent_id")
    entity_id: str = Field(description="Target client_id or partner_id")
    action_type: str = Field(description="Action proposed / executed")
    treatment_assigned: int = Field(ge=0, le=1, description="1 if executed, 0 if rejected or aborted")
    propensity_score: float = Field(ge=0.0, le=1.0, description="Estimated propensity score e(X) at proposal")
    causal_features: dict[str, float] = Field(description="Covariate vector X at decision time")
    manager_override_flag: bool = Field(default=False, description="True if human altered agent recommendation")
    override_reason: str | None = Field(default=None, description="Documented reason for human override")
    observed_retained_revenue_30d: float | None = Field(default=None, description="Retained revenue at 30 days")
    observed_retained_revenue_60d: float | None = Field(default=None, description="Retained revenue at 60 days")
    actual_churn_60d: bool | None = Field(default=None, description="Whether entity churned at 60 days")
    clawback_recovered_usd_90d: float | None = Field(default=None, description="Total funds recovered at 90 days")
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Proposal record timestamp")
    reconciled_at: datetime | None = Field(default=None, description="Horizon reconciliation timestamp")


class AuditVerificationReport(BaseModel):
    """Output emitted by ContinuousAuditWalker after verifying hash chain and WORM anchors."""

    report_id: str = Field(description="Unique UUID identifying the audit run")
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Audit execution timestamp")
    total_entries: int = Field(ge=0, description="Total ledger entries inspected")
    genesis_hash: str = Field(description="Genesis anchor hash verified at sequence 1")
    head_hash: str = Field(description="Cryptographic hash digest of latest chain entry")
    is_valid: bool = Field(description="True if 100% of links and WORM anchors match, False otherwise")
    integrity_score: float = Field(ge=0.0, le=1.0, description="Proportion of verified valid links (1.0 = valid)")
    tampered_sequence_id: int | None = Field(default=None, description="Exact ledger_seq where corruption occurred")
    failure_reason: str | None = Field(default=None, description="Detailed failure diagnostics")
    worm_checkpoints_verified: int = Field(default=0, description="Count of WORM anchor proofs matched")
    audit_duration_ms: float = Field(default=0.0, ge=0.0, description="Traversal latency in milliseconds")
