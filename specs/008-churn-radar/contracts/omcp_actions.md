# Canonical OMCP Tool Contracts: Partner Churn Radar (Module C / Slice S2)

**Branch**: `008-churn-radar` | **Date**: 2026-10-07  
**Standard**: Ontology Model Context Protocol (OMCP) Canonical Interface Standard  
**Authoritative References**: `initial_plan.md` §3.1, §4, `FEIOS/src/eios/ontology/omcp/server.py`, `FEIOS/src/eios/ontology/actions/intent_hub.py`

---

## 1. Overview & Protocol Semantics

All interactions between the reasoning mesh (`ChurnRadarSpecialist`, `ConversationEngine`), the front-end Workshop cockpit, and the underlying data layer occur strictly through **OMCP tools**. 

Per Constitution Principle IV (Ontology-Only Access) and Principle II (No Autonomous Write-Back):
1. Agents read partner signals and hazard scores strictly through typed read tools.
2. Agents NEVER write to databases directly; they emit proposed actions through `propose_action`.
3. Every response is subject to Security Markings (`OMCP Security Marking Enforcer`).

---

## 2. Tool Contract 1: `get_partner_signals`

**Description**: Retrieves calibrated 30-day hazard probabilities, priority scores, change-point markers, top contributing signal families, and audited plain-text explanations for a given partner.

### 2.1 Request Schema
```json
{
  "type": "object",
  "properties": {
    "partner_id": {
      "type": "string",
      "description": "Canonical partner identifier (e.g. 'P-CHURN-DRIFT', 'P-1002')",
      "minLength": 4
    },
    "window_days": {
      "type": "integer",
      "description": "Evaluation observation window (default 30 days)",
      "default": 30
    }
  },
  "required": ["partner_id"]
}
```

### 2.2 Response Schema
```json
{
  "type": "object",
  "properties": {
    "partner_id": { "type": "string" },
    "tier": { "type": "string", "enum": ["TIER_1", "TIER_2", "TIER_3", "VIP_MASTER"] },
    "region_id": { "type": "string" },
    "value_at_risk_usd": { "type": "number" },
    "hazard_probability_30d": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
    "priority_score": { "type": "number", "description": "hazard_probability_30d * value_at_risk_usd" },
    "risk_tier": { "type": "string", "enum": ["HIGH", "MEDIUM", "LOW"] },
    "intervention_window": { "type": "string", "enum": ["OPTIMAL", "LATE_STAGE", "EARLY_WATCH", "STABLE"] },
    "change_point_detected": { "type": "boolean" },
    "top_contributing_signals": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "signal_family": { "type": "string", "enum": ["BEHAVIORAL", "COMMUNICATION", "RELATIONSHIP", "FINANCIAL", "COMPETITIVE"] },
          "metric_name": { "type": "string" },
          "observed_value": { "type": "number" },
          "baseline_value": { "type": "number" },
          "relative_delta": { "type": "number" },
          "citation_ref": { "type": "string" }
        },
        "required": ["signal_family", "metric_name", "observed_value", "relative_delta", "citation_ref"]
      }
    },
    "explanation": {
      "type": "object",
      "properties": {
        "narrative": { "type": "string" },
        "citations": { "type": "array", "items": { "type": "string" } },
        "is_replay": { "type": "boolean" }
      },
      "required": ["narrative", "citations"]
    }
  },
  "required": [
    "partner_id",
    "hazard_probability_30d",
    "priority_score",
    "risk_tier",
    "intervention_window",
    "change_point_detected",
    "top_contributing_signals",
    "explanation"
  ]
}
```

---

## 3. Tool Contract 2: `get_high_risk_cohorts`

**Description**: Identifies systemic regional or segment-level disengagement clusters where multiple partners exhibit synchronized churn shocks (e.g. regional competitor campaigns).

### 3.1 Request Schema
```json
{
  "type": "object",
  "properties": {
    "min_priority_score": {
      "type": "number",
      "description": "Minimum aggregate priority score threshold to filter cohorts",
      "default": 10000.0
    },
    "min_p_value": {
      "type": "number",
      "description": "Significance threshold under permutation cluster test",
      "default": 0.01
    }
  }
}
```

### 3.2 Response Schema
```json
{
  "type": "object",
  "properties": {
    "cohorts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "cohort_id": { "type": "string" },
          "region_id": { "type": "string" },
          "partner_count": { "type": "integer" },
          "affected_partner_ids": { "type": "array", "items": { "type": "string" } },
          "aggregate_value_at_risk_usd": { "type": "number" },
          "p_value": { "type": "number" },
          "common_driver": { "type": "string" },
          "recommended_playbook": { "type": "string" }
        },
        "required": [
          "cohort_id",
          "region_id",
          "partner_count",
          "affected_partner_ids",
          "aggregate_value_at_risk_usd",
          "p_value",
          "common_driver",
          "recommended_playbook"
        ]
      }
    }
  },
  "required": ["cohorts"]
}
```

---

## 4. Tool Contract 3: `propose_action` (Action Type: `LaunchRetentionPlaybook`)

**Description**: Emits a cryptographically signed, non-autonomous `ActionIntentToken` proposing a retention intervention. Conforms strictly to platform `ActionIntentHub`.

### 4.1 Request Schema
```json
{
  "type": "object",
  "properties": {
    "action_type": {
      "type": "string",
      "enum": ["LaunchRetentionPlaybook"],
      "description": "Governed canonical action type"
    },
    "parameters": {
      "type": "object",
      "properties": {
        "partner_ids": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of partner IDs targeted by the intervention"
        },
        "playbook_id": {
          "type": "string",
          "enum": ["VIP_COMMISSION_BOOST", "DEDICATED_CSM_OUTREACH", "COMPETITIVE_MATCH_CAMPAIGN"],
          "description": "Pre-approved retention playbook"
        },
        "budget": {
          "type": "number",
          "description": "Approved retention budget in USD"
        }
      },
      "required": ["partner_ids", "playbook_id", "budget"]
    },
    "evidence_refs": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of L1 Data Product or Entity citations justifying the intervention"
    },
    "propensity_score": {
      "type": "number",
      "description": "Estimated assignment propensity e(X) for Doubly Robust AIPW",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "causal_context": {
      "type": "object",
      "description": "Snapshot of partner risk features at time of proposal"
    }
  },
  "required": ["action_type", "parameters", "evidence_refs", "propensity_score"]
}
```

### 4.2 Response Schema
```json
{
  "type": "object",
  "properties": {
    "intent_id": { "type": "string" },
    "action_type": { "type": "string" },
    "severity": { "type": "string", "enum": ["LOW", "MEDIUM", "HIGH"] },
    "status": { "type": "string", "enum": ["PENDING"] },
    "nonce": { "type": "string" },
    "issued_at": { "type": "string", "format": "date-time" },
    "expires_at": { "type": "string", "format": "date-time" },
    "signature": { "type": "string", "description": "Base64 ECDSA P-256 signature" },
    "kms_key_id": { "type": "string" }
  },
  "required": [
    "intent_id",
    "action_type",
    "severity",
    "status",
    "nonce",
    "issued_at",
    "expires_at",
    "signature",
    "kms_key_id"
  ]
}
```
