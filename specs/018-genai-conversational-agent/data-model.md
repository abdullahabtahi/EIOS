# Phase 1 Data Model: Production-Grade Gen AI Conversational Agent Mesh (F018)

**Feature Branch**: `018-genai-conversational-agent`  
**Date**: 2026-10-10  
**Status**: Completed  

---

## 1. Domain Entities & Pydantic v2 Schemas

```text
┌───────────────────────┐         ┌────────────────────────┐
│  ConversationSession  │ 1─────* │    BlackboardState     │
│  (Session & Thread)   │         │ (Multi-Agent Memory)   │
└───────────────────────┘         └───────────┬────────────┘
                                              │ 1
                                              ▼ *
                                  ┌────────────────────────┐
                                  │   ToolExecutionTrace   │
                                  │   (OMCP & Search Logs) │
                                  └───────────┬────────────┘
                                              │ 1
                         ┌────────────────────┴────────────────────┐
                         ▼ 0..1                                    ▼ 1
              ┌──────────────────────┐                  ┌──────────────────────┐
              │  ActionIntentToken   │                  │    AuditorRecord     │
              │  (KMS P-256 Signed)  │                  │  (Principle I Egress)│
              └──────────────────────┘                  └──────────────────────┘
```

---

### 1.1 Session & State Models

```python
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OperatorRole(str, Enum):
    EXECUTIVE = "executive"
    AML_INVESTIGATOR = "aml_investigator"
    PARTNER_MANAGER = "partner_manager"
    COMPLIANCE_AUDITOR = "compliance_auditor"
    DATA_OPERATIONS = "data_operations"


class SpecialistRoute(str, Enum):
    EXECUTIVE_SYNTHESIS = "ExecutiveSynthesis"
    AML_INVESTIGATOR = "AMLInvestigator"
    PARTNER_RETENTION = "PartnerRetention"
    PARTNER_FRAUD = "PartnerFraud"
    GOVERNANCE_COMPLIANCE = "GovernanceCompliance"


class ConversationSession(BaseModel):
    """Durable conversation session state persisted in Firestore."""
    session_id: str = Field(description="Unique session identifier")
    thread_id: str = Field(description="LangGraph checkpointer thread identifier")
    operator_id: str = Field(description="Authenticated operator officer ID")
    operator_role: OperatorRole = Field(description="Active operator role context")
    active_entity_anchor: Optional[str] = Field(default=None, description="Currently focused entity (e.g. CR84920, AP-1029)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_turn_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    turn_count: int = Field(default=0, ge=0)


class BlackboardState(BaseModel):
    """Shared multi-agent state matching the QuantumBlack Blackboard topology."""
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Ordered conversation turn history")
    next_agent: str = Field(default="supervisor", description="Next designated agent node or FINISH")
    active_route: SpecialistRoute = Field(default=SpecialistRoute.EXECUTIVE_SYNTHESIS)
    reflection_cycles: int = Field(default=0, ge=0, le=3, description="Bounded deliberation cycles (max 3)")
    entity_anchors: Dict[str, str] = Field(default_factory=dict, description="Resolved entity dictionary")
    extracted_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Ground-truth facts collected by tools")
    staged_actions: List[Dict[str, Any]] = Field(default_factory=list, description="Staged action intent proposals")
    compliance_hold: bool = Field(default=False, description="Flag indicating active AML/fraud freeze")
    final_response: str = Field(default="", description="Assembled executive narrative prose")
```

---

### 1.2 Tool Execution & Provenance Models

```python
class CitationType(str, Enum):
    METRIC = "METRIC"
    ENTITY = "ENTITY"
    STATUTORY_POLICY = "STATUTORY_POLICY"
    PRECEDENT = "PRECEDENT"


class ProvenanceCitation(BaseModel):
    """Audit-proof citation referencing an exact metric, entity, or policy document."""
    citation_type: CitationType
    citation_id: str = Field(description="Identifier (e.g. net_deposit_volume_30d_usd, 31 CFR § 1020.320)")
    label: str = Field(description="Human-readable citation label")
    source_engine: str = Field(description="Originating engine (SemanticRegistry.DuckDB, VertexAISearch, etc.)")
    as_of: datetime = Field(default_factory=lambda: datetime.now(UTC))
    formula_version: Optional[str] = None


class ToolExecutionTrace(BaseModel):
    """Structured record of an OMCP or Vertex Search tool execution."""
    tool_name: str
    arguments: Dict[str, Any]
    output_payload: Dict[str, Any]
    source_engine: str
    latency_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

---

### 1.3 Governance & Action Intent Models

```python
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


class ActionIntentToken(BaseModel):
    """Cryptographically signed action proposal enforcing Principle II (No Autonomous Write-Back)."""
    intent_id: str
    action_type: str = Field(description="Governed Action Type (e.g. HoldWithdrawal, DeployRetentionPlaybook)")
    target_entity_id: str
    parameters: Dict[str, Any]
    evidence_refs: List[str]
    severity: ActionSeverity = ActionSeverity.HIGH
    status: ActionStatus = ActionStatus.STAGED_FOR_REVIEW
    nonce: str = Field(description="Single-use cryptographic nonce")
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(description="15-minute expiration timestamp")
    requester_agent_id: str
    kms_key_id: str = Field(description="Cloud KMS Key Ring path")
    signature: str = Field(description="ECDSA P-256 digital signature over intent digest")
    requires_four_eyes: bool = True
```

---

### 1.4 Auditor Egress Verification Models

```python
class AuditorStatus(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class AuditorRecord(BaseModel):
    """Output of the Metric Auditor Gate egress firewall enforcing Principle I."""
    passed: bool
    status: AuditorStatus
    verified_numerical_anchors: List[float] = Field(default_factory=list)
    unanchored_tokens: List[str] = Field(default_factory=list)
    exempted_statutory_citations: List[str] = Field(default_factory=list)
    relative_tolerance: float = 0.01
    audited_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str
```
