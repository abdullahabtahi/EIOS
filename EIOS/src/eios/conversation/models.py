"""Domain entities and Pydantic v2 schemas for the conversational reasoning mesh (F018)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


class OperatorRole(str, Enum):
    EXECUTIVE = "executive"
    AML_INVESTIGATOR = "aml_investigator"
    PARTNER_MANAGER = "partner_manager"
    COMPLIANCE_AUDITOR = "compliance_auditor"
    DATA_OPERATIONS = "data_operations"


class SpecialistDomain(StrEnum):
    SYNTHESIS = "Synthesis"
    SENTINEL_AML = "SentinelAML"
    CHURN_RADAR = "ChurnRadar"
    PARTNER_FRAUD = "PartnerFraud"
    GOVERNANCE = "Governance"


class SpecialistRoute(str, Enum):
    EXECUTIVE_SYNTHESIS = "ExecutiveSynthesis"
    AML_INVESTIGATOR = "AMLInvestigator"
    PARTNER_RETENTION = "PartnerRetention"
    PARTNER_FRAUD = "PartnerFraud"
    GOVERNANCE_COMPLIANCE = "GovernanceCompliance"


class CitationType(str, Enum):
    METRIC = "METRIC"
    ENTITY = "ENTITY"
    STATUTORY_POLICY = "STATUTORY_POLICY"
    PRECEDENT = "PRECEDENT"


class ActionSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionStatus(str, Enum):
    PENDING = "PENDING"
    STAGED_FOR_REVIEW = "STAGED_FOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


class AuditorStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class ConversationSession(BaseModel):
    """Durable conversation session state persisted in Firestore/SQLite."""

    session_id: str = Field(description="Unique session identifier")
    thread_id: str = Field(description="LangGraph checkpointer thread identifier")
    operator_id: str = Field(description="Authenticated operator officer ID")
    operator_role: OperatorRole = Field(
        default=OperatorRole.EXECUTIVE, description="Active operator role context"
    )
    active_entity_anchor: str | None = Field(
        default=None, description="Currently focused entity (e.g. CR84920, AP-1029)"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_turn_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    turn_count: int = Field(default=0, ge=0)


class ProvenanceCitation(BaseModel):
    """Audit-proof citation referencing an exact metric, entity, or policy document."""

    citation_type: CitationType
    citation_id: str = Field(
        description="Identifier (e.g. net_deposit_volume_30d_usd, 31 CFR § 1020.320)"
    )
    label: str = Field(description="Human-readable citation label")
    source_engine: str = Field(
        description="Originating engine (SemanticRegistry.DuckDB, VertexAISearch, etc.)"
    )
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    formula_version: str | None = None


class ToolExecutionTrace(BaseModel):
    """Structured record of an OMCP or Vertex Search tool execution."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    source_engine: str = "OMCP"
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ActionIntentToken(BaseModel):
    """Cryptographically signed action proposal enforcing Principle II (No Autonomous Write-Back)."""

    intent_id: str
    action_type: str = Field(
        description="Governed Action Type (e.g. HoldWithdrawal, DeployRetentionPlaybook)"
    )
    target_entity_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    severity: ActionSeverity = ActionSeverity.HIGH
    status: ActionStatus = ActionStatus.STAGED_FOR_REVIEW
    nonce: str = Field(description="Single-use cryptographic nonce")
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(description="15-minute expiration timestamp")
    requester_agent_id: str = "agent_supervisor"
    kms_key_id: str = Field(
        default="projects/spatial-cat-489006-a4/locations/us-central1/keyRings/gov/cryptoKeys/p256"
    )
    signature: str = Field(default="MEYCIQDf_SIMULATED_ECDSA_P256_SIG")
    requires_four_eyes: bool = True


class AuditorRecord(BaseModel):
    """Output of the Metric Auditor Gate egress firewall enforcing Principle I."""

    passed: bool
    status: AuditorStatus
    verified_numerical_anchors: list[float] = Field(default_factory=list)
    unanchored_tokens: list[str] = Field(default_factory=list)
    exempted_statutory_citations: list[str] = Field(default_factory=list)
    relative_tolerance: float = 0.01
    audited_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str = "tr_default"


class RouteDecision(BaseModel):
    route: SpecialistDomain
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = Field(default="")
    refusal_required: bool = Field(default=False)
    refusal_reason: str | None = None
    extracted_entities: dict[str, str] = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    tool_name: str
    entity_id: str | None = None
    metric_name: str
    value: float | str
    unit: str | None = None
    as_of: str
    definition_version: str


class BlackboardState(BaseModel):
    """Shared multi-agent state matching the QuantumBlack Blackboard topology."""

    messages: list[dict[str, Any]] = Field(default_factory=list)
    next_agent: str = Field(default="supervisor")
    active_route: SpecialistRoute = Field(default=SpecialistRoute.EXECUTIVE_SYNTHESIS)
    reflection_cycles: int = Field(default=0, ge=0, le=3, description="Hard-capped at 3 cycles")
    entity_anchors: dict[str, str] = Field(default_factory=dict)
    extracted_evidence: list[dict[str, Any]] = Field(default_factory=list)
    staged_actions: list[dict[str, Any]] = Field(default_factory=list)
    compliance_hold: bool = Field(default=False)
    final_response: str = Field(default="")


class ConversationQueryRequest(BaseModel):
    session_id: str | None = None
    user_query: str
    user_role: str = "Executive"
    context_filters: dict[str, Any] = Field(default_factory=dict)


class ConversationQueryResponse(BaseModel):
    session_id: str
    turn_index: int = 1
    route: SpecialistDomain = SpecialistDomain.SYNTHESIS
    response_markdown: str
    citations: list[str] = Field(default_factory=list)
    provenance_citations: list[ProvenanceCitation] = Field(default_factory=list)
    evidence_ledger: list[EvidenceItem] = Field(default_factory=list)
    staged_recommendation: dict[str, Any] | None = None
    is_replay_fallback: bool = False
    fallback_reason: str | None = None
    turn_latency_ms: float = 0.0
    reflection_cycles_used: int = 0
    auditor_status: str | None = "PASS"


def sanitize_for_state_storage(obj: Any) -> Any:
    """Pre-mortem sanitization preventing Firestore 1MB blowout and Python/NumPy serialization bugs."""
    if isinstance(obj, dict):
        return {str(k): sanitize_for_state_storage(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_for_state_storage(x) for x in obj]
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, (np.generic,)):
        return obj.item()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj
