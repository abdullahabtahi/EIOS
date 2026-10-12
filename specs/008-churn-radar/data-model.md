# Domain Data Models & Schemas: Partner Churn Radar (Module C / Slice S2)

**Branch**: `008-churn-radar` | **Date**: 2026-10-07  
**Standard**: Palantir Foundry Kinetic Ontology × Pydantic v2 Production Contracts  
**Authoritative References**: `initial_plan.md` §4, §6.1, `FEIOS/src/eios/ontology/core/objects.py`, `FEIOS/src/eios/ontology/actions/intent_hub.py`, `FEIOS/src/eios/contracts/models.py`

---

## 1. Kinetic Ontology Domain Entities

### 1.1 Extended Kinetic Object: `Partner`
The Churn Radar dynamically enriches the canonical `Partner` ontology object hydrated from `partner_360` (DP 6).

```python
from datetime import UTC, datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
from eios.ontology.core.base import OntologyObject
from eios.ontology.core.interfaces import TransactingEntity

class SignalContribution(BaseModel):
    """Deterministic contribution of an individual signal family feature."""
    signal_family: Literal["BEHAVIORAL", "COMMUNICATION", "RELATIONSHIP", "FINANCIAL", "COMPETITIVE"]
    metric_name: str
    observed_value: float
    baseline_value: float
    relative_delta: float
    hazard_weight: float
    citation_ref: str = Field(..., description="Canonical L1 Data Product citation (e.g. DP9:partner_engagement_signals)")

class ChurnExplanationRecord(BaseModel):
    """Audited plain-language root-cause narrative synthesized from tool outputs."""
    explanation_id: str
    partner_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    narrative: str
    citations: list[str] = Field(default_factory=list)
    is_replay: bool = False

class Partner(OntologyObject, TransactingEntity):
    """Canonical Affiliate / Introducing Broker with Churn Radar Kinetic Properties."""
    partner_id: str
    tier: Literal["TIER_1", "TIER_2", "TIER_3", "VIP_MASTER"] = "TIER_2"
    region_id: str | None = None
    tenure_days: int = 0
    value_at_risk_usd: float = 0.0
    manager_id: str | None = None

    # --- Churn Radar Dynamic Properties (Slice S2) ---
    hazard_probability_30d: float = Field(default=0.0, ge=0.0, le=1.0)
    priority_score: float = Field(default=0.0, ge=0.0, description="hazard_probability_30d * value_at_risk_usd")
    risk_tier: Literal["HIGH", "MEDIUM", "LOW"] = "LOW"
    intervention_window: Literal["OPTIMAL", "LATE_STAGE", "EARLY_WATCH", "STABLE"] = "STABLE"
    change_point_flag: bool = False
    top_contributing_signals: list[SignalContribution] = Field(default_factory=list)
    churn_explanation: ChurnExplanationRecord | None = None

    @property
    def primary_key(self) -> str:
        return self.partner_id

    def get_risk_rating(self) -> str:
        return self.risk_tier
```

---

## 2. Systemic Cohort Risk Entities

### 2.1 `CohortAnomalyAlert`
Captures regional and segment-level synchronized disengagement shocks.

```python
class CohortAnomalyAlert(BaseModel):
    """Systemic regional or segment disengagement cluster alert."""
    alert_id: str
    region_id: str
    partner_count: int
    affected_partner_ids: list[str]
    aggregate_value_at_risk_usd: float
    p_value: float = Field(..., description="Statistical significance under permutation test")
    common_driver: str = Field(..., description="e.g. Regional Competitor Zero-Spread Promotion")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["ACTIVE", "ACKNOWLEDGED", "RESOLVED"] = "ACTIVE"
    recommended_playbook: str = "LaunchRegionalAffiliateIncentive"
```

---

## 3. Governed Action Intent & Flywheel Entities

### 3.1 `ActionIntentToken` (Conforming to Platform Action Hub)
Strictly matches `FEIOS/src/eios/ontology/actions/intent_hub.py` and `initial_plan.md` §6.1.

```python
from enum import StrEnum

class ActionSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ActionStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"

class ActionIntentToken(BaseModel):
    """Cryptographically signed, non-autonomous intervention proposal."""
    intent_id: str
    action_type: str = "LaunchRetentionPlaybook"
    parameters: dict[str, Any] = Field(
        ..., 
        description="Must satisfy CANONICAL_ACTION_SPECS: partner_ids, playbook_id, budget"
    )
    evidence_refs: list[str]
    severity: ActionSeverity = ActionSeverity.MEDIUM
    status: ActionStatus = ActionStatus.PENDING
    nonce: str
    issued_at: datetime
    expires_at: datetime
    requester_agent_id: str = "agent_churn_radar"
    kms_key_id: str
    signature: str = ""
    propensity_score: float = Field(
        default=0.5, 
        ge=0.0, 
        le=1.0, 
        description="Estimated propensity e(X) stamped for Doubly Robust AIPW"
    )
    causal_context: dict[str, Any] = Field(
        default_factory=dict, 
        description="Snapshot of covariates X at intervention time"
    )
```

### 3.2 Decision Ledger & Outcome Records (The Flywheel)
```python
class DecisionLedgerEntry(BaseModel):
    """Immutable, append-only record in the simulated write-back sink."""
    ledger_seq: int
    intent_id: str
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action_type: str
    parameters: dict[str, Any]
    prev_hash: str
    current_hash: str

class DecisionOutcomeRecord(BaseModel):
    """Forward outcome record used for Doubly Robust AIPW causal estimation."""
    outcome_id: str
    intent_id: str
    partner_id: str
    playbook_id: str
    treatment_assigned: int = Field(..., description="1 if treated, 0 if control")
    propensity_score_e: float
    observed_retained_revenue_60d: float
    actual_churn_60d: bool
    recorded_at: datetime
```

---

## 4. GenAI Pattern Discovery Contracts

### 4.1 `DisengagementTheme`
Structured egress schema extracted by the `PatternDiscoverySpecialist`.

```python
class DisengagementTheme(BaseModel):
    """Structured hypothesis of an emerging churn pattern discovered in tickets."""
    theme_id: str
    title: str = Field(..., description="Concise theme title (e.g. MT5 WebSocket Rate Limit Frustration)")
    affected_partner_count: int
    signal_families_implicated: list[str]
    confidence_score: float = Field(ge=0.0, le=1.0)
    supporting_ticket_ids: list[str]
    plain_language_summary: str
    actionable_remediation: str
```

---

## 5. DuckDB Hot State Schema (DDL)

The Churn Radar maintains high-speed hot state tables in DuckDB to guarantee sub-50ms query latency via OMCP:

```sql
-- 1. Churn Radar Partner Scores Table
CREATE TABLE IF NOT EXISTS churn_radar_scores (
    partner_id VARCHAR PRIMARY KEY,
    as_of_date DATE NOT NULL,
    hazard_probability_30d DOUBLE NOT NULL,
    priority_score DOUBLE NOT NULL,
    risk_tier VARCHAR NOT NULL,             -- 'HIGH', 'MEDIUM', 'LOW'
    intervention_window VARCHAR NOT NULL,   -- 'OPTIMAL', 'LATE_STAGE', 'EARLY_WATCH', 'STABLE'
    change_point_flag BOOLEAN NOT NULL,
    top_driver_family VARCHAR NOT NULL,
    top_driver_metric VARCHAR NOT NULL,
    top_driver_delta DOUBLE NOT NULL,
    narrative_summary VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Systemic Cohort Alerts Table
CREATE TABLE IF NOT EXISTS churn_cohort_alerts (
    alert_id VARCHAR PRIMARY KEY,
    region_id VARCHAR NOT NULL,
    partner_count INTEGER NOT NULL,
    aggregate_value_at_risk DOUBLE NOT NULL,
    p_value DOUBLE NOT NULL,
    common_driver VARCHAR NOT NULL,
    recommended_playbook VARCHAR NOT NULL,
    detected_at TIMESTAMP NOT NULL,
    status VARCHAR DEFAULT 'ACTIVE'
);

-- 3. Decision Outcomes Ledger (The Flywheel Store)
CREATE TABLE IF NOT EXISTS decision_outcomes_ledger (
    outcome_id VARCHAR PRIMARY KEY,
    intent_id VARCHAR NOT NULL,
    partner_id VARCHAR NOT NULL,
    playbook_id VARCHAR NOT NULL,
    treatment_assigned INTEGER NOT NULL,    -- 1 or 0
    propensity_score DOUBLE NOT NULL,
    observed_retained_revenue_60d DOUBLE NOT NULL,
    actual_churn_60d BOOLEAN NOT NULL,
    recorded_at TIMESTAMP NOT NULL
);
```
