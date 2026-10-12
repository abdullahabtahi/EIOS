# Data Model & Domain Entities: Institutional Operator Cockpit (016-cockpit-frontend)

**Branch**: `016-cockpit-frontend` | **Date**: 2026-10-10 | **Feature Spec**: [spec.md](file:///Users/abdullahabtahi/Real-Time%20Enterprise%20Intelligence%20Agent/specs/016-cockpit-frontend/spec.md)

This document formalizes the frontend domain entities, TypeScript interface contracts, and validation rules governing the Institutional Operator Cockpit.

---

## 1. Domain Entities & TypeScript Definitions

### 1.1 Operator Persona & Workstation Session

```typescript
export type PersonaRole =
  | 'executive'
  | 'aml_investigator'
  | 'partner_manager'
  | 'compliance_auditor'
  | 'data_operations';

export interface OperatorIdentity {
  officerId: string;
  name: string;
  email: string;
  role: PersonaRole;
  clearanceLevel: 'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3_EXECUTIVE';
  idpClaim: string;
  sessionNonce: string;
}

export interface CockpitSession {
  sessionId: string;
  activeRole: PersonaRole;
  operator: OperatorIdentity;
  activeTriageItemId: string | null;
  triageFilter: {
    status?: TriageStatus;
    severity?: SeverityLevel;
    searchQuery?: string;
  };
  governedActionShelfExpanded: boolean;
  stagedActionsCount: number;
  isSimulatedOutage: boolean; // Triggers [REPLAY] fallback mode
  systemLatencyMs: number;
}
```

---

### 1.2 Triage Queue Item

```typescript
export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type TriageStatus = 'OPEN' | 'INVESTIGATING' | 'STAGED' | 'RESOLVED' | 'DISMISSED';

export interface TriageItem {
  id: string;
  role: PersonaRole;
  title: string;
  subtitle: string;
  entityId: string;
  entityType: 'ACCOUNT' | 'PARTNER' | 'TRANSACTION_CLUSTER' | 'BRIEFING' | 'LEDGER_CHECKPOINT';
  priorityScore: number; // 0.00 to 1.00
  severity: SeverityLevel;
  status: TriageStatus;
  timestamp: string; // ISO 8601
  tags: string[];
  metricsSummary: Record<string, number | string>;
}
```

---

### 1.3 Deterministic Metric Provenance

```typescript
export type ProvenanceCitation =
  | '[BRIEF]'
  | '[ASSUMPTION]'
  | '[ILLUSTRATIVE]'
  | '[TARGET]'
  | '[SPIKE]';

export interface MetricProvenance {
  metricId: string;
  name: string;
  rawValue: number | string;
  formattedValue: string;
  unit?: string;
  semanticDefinitionVersion: string; // e.g. "v2.4.1 [d8a9f2]"
  asOfTimestamp: string; // ISO 8601
  originEngine: 'duckdb:semantic_layer' | 'bigquery:metrics_job' | 'realtime:flink' | 'offline:scm';
  stewardRole: string; // e.g. "VP Finance", "Lead AML Officer"
  citation: ProvenanceCitation;
  isCached: boolean;
}
```

---

### 1.4 Copilot Dossier & Investigation Evidence

```typescript
export interface DossierSection {
  sectionId: string;
  title: string;
  narrativeText: string;
  citations: string[];
  metrics: MetricProvenance[];
  isFallbackReplay?: boolean;
}

export interface TradeOffCard {
  proposedAction: string;
  projectedReturn: string;
  projectedRisk: string;
  confidenceScore: number; // 0.00 to 1.00
  downsideSensitivity: string;
  evidenceCitations: string[];
}

export interface SarDraftDocument {
  caseId: string;
  subjectName: string;
  subjectAccountId: string;
  suspiciousActivityType: string;
  summaryNarrative: string;
  transactionHistorySummary: string;
  totalTurnover: number;
  netLossProfitRatio: number;
  statutoryCitations: string[];
  generatedTimestamp: string;
  status: 'DRAFT' | 'READY_FOR_FILING' | 'FILED';
}

export interface CopilotDossier {
  dossierId: string;
  entityId: string;
  role: PersonaRole;
  headline: string;
  executiveSummary: string;
  sections: DossierSection[];
  tradeOffs?: TradeOffCard[];
  sarDraft?: SarDraftDocument;
  asOfTimestamp: string;
  isCachedSnapshot: boolean;
  replayReason?: string;
}
```

---

### 1.5 Kinetic Analytical Visualizations

#### Causal DAG & Parametric What-If Propagation

```typescript
export type CausalEdgeStatus = 'VERIFIED_CAUSAL' | 'CORRELATION_ONLY';

export interface CausalNode {
  id: string;
  domain: 'COMPETITIVE' | 'PARTNER' | 'CLIENT' | 'FINANCIAL';
  label: string;
  baseValue: number;
  shockedValue: number;
  unit: string;
  isDirectTarget: boolean;
}

export interface CausalEdge {
  id: string;
  source: string;
  target: string;
  coefficient: number;
  pValue: number;
  placeboRefuterPValue: number;
  confidence: number; // >= 0.80 for causal
  status: CausalEdgeStatus; // VERIFIED_CAUSAL iff confidence >= 0.80 && placeboRefuterPValue > 0.05
}

export interface WaterfallAttributionItem {
  driverName: string;
  deltaAmount: number;
  percentageShare: number; // Sum of all percentageShares MUST equal 100.0% (+/- 0.01%)
  isPositive: boolean;
}

export interface CausalDagPayload {
  dagId: string;
  nodes: CausalNode[];
  edges: CausalEdge[];
  whatIfParameter: {
    name: string;
    minValue: number;
    maxValue: number;
    currentValue: number;
    step: number;
    unit: string;
  };
  attributionWaterfall: WaterfallAttributionItem[];
}
```

#### Topological Relational Graph & CGNAT Hub Suppression

```typescript
export type GraphNodeType = 'ACCOUNT' | 'DEVICE' | 'IP_ADDRESS' | 'PAYMENT_METHOD';
export type GraphEdgeType = 'SHARED_IP' | 'SHARED_DEVICE' | 'TRANSACTION_FLOW' | 'MIRROR_TRADE';

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  degree: number;
  isCgnatHub: boolean;
  isSuppressed: boolean;
  riskScore: number;
  details: Record<string, string>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  weight: number;
  label?: string;
}

export interface TopologicalGraphPayload {
  graphId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  hubSuppressionThreshold: number; // e.g. degree >= 15 triggers suppression
  activeSuppressionCount: number;
}
```

#### Partner Churn Radar & 3-Tier Tree Visualizer

```typescript
export interface PartnerChurnItem {
  partnerId: string;
  name: string;
  tier: 'TIER_1_SUPER' | 'TIER_2_MASTER' | 'TIER_3_AFFILIATE';
  pChurn: number; // 0.00 to 1.00
  valueAtRiskUsd: number;
  daysToChurn: number;
  changePointDetected: boolean;
  mirrorTradeCorrelation: number; // 0.00 to 1.00
  extractedCommissionUsd: number;
}

export interface PartnerHierarchyNode {
  partnerId: string;
  name: string;
  tierLevel: 1 | 2 | 3;
  monthlyCommissionUsd: number;
  subAffiliatesCount: number;
  children?: PartnerHierarchyNode[];
}
```

---

### 1.6 Governed Action Shelf & Two-Phase Commit

```typescript
export type ActionIntentType =
  | 'HOLD_WITHDRAWAL'
  | 'LAUNCH_RETENTION_PLAYBOOK'
  | 'FREEZE_PARTNER_COMMISSION'
  | 'CLAWBACK_COMMISSION'
  | 'TUNE_MONITORING_THRESHOLD'
  | 'FILE_SAR_SUBMISSION';

export type ActionLifecycleState =
  | 'STAGED'
  | 'PENDING_SECOND_EYE'
  | 'COMMITTED'
  | 'REJECTED'
  | 'EXPIRED';

export interface FourEyesApprovalRecord {
  initiatorOfficerId: string;
  initiatorTimestamp: string;
  secondOfficerId?: string;
  secondOfficerTimestamp?: string;
  approvalRationale?: string;
  idpClaimValidation: boolean;
}

export interface ActionIntentCard {
  intentId: string;
  actionType: ActionIntentType;
  targetEntityId: string;
  targetEntityType: string;
  severity: SeverityLevel;
  lifecycleState: ActionLifecycleState;
  stagedTimestamp: string;
  expiresAt: string; // 15-minute TTL
  parameters: Record<string, any>;
  estimatedImpact: string;
  kmsSignatureBadge: {
    keyId: string;
    algorithm: 'ECDSA_SHA256_P256';
    signatureDigest: string;
    verified: boolean;
  };
  fourEyesRecord: FourEyesApprovalRecord;
}
```

---

### 1.7 Compliance Ledger & Data Operations SLO Health

```typescript
export interface LedgerAuditRecord {
  ledgerSeq: number;
  recordHash: string;
  previousHash: string;
  actionIntentId: string;
  actionType: string;
  targetEntity: string;
  approverClaims: string[];
  timestamp: string;
  wormLocked: boolean;
  chainVerificationStatus: 'VALID' | 'TAMPERED';
}

export interface SloHealthItem {
  sloId: string;
  name: string;
  targetValue: string;
  currentValue: string;
  status: 'HEALTHY' | 'DEGRADED' | 'BREACHED';
  errorBudgetRemainingPct: number;
  freshnessLatencySec: number;
  dlqQuarantineDepth: number;
}
```

---

### 1.8 Conversational Copilot & Metric Auditor Gate (Feature 007)

```typescript
export interface CopilotQueryRequest {
  naturalLanguageQuery: string;
  activeRole: PersonaRole;
  contextEntityId?: string;
}

export interface AuditorGateResult {
  auditPassed: boolean;
  extractedNumbers: (number | string)[];
  anchoredNumbers: (number | string)[];
  untraceableNumbers: (number | string)[];
  rejectionReason?: string;
  toolTracesCount: number;
}

export interface CopilotQueryResponse {
  queryId: string;
  naturalLanguageQuery: string;
  responseMarkdown: string;
  citedMetrics: MetricProvenance[];
  suggestedAction?: ActionIntentCard;
  auditorResult: AuditorGateResult;
  timestamp: string;
}
```

---

### 1.9 Active Learning Flywheel Feedback & Outcomes (Feature 014)

```typescript
export type FlywheelFeedbackType =
  | 'SAR_NARRATIVE_CORRECTION'
  | 'FALSE_POSITIVE_ALERT_DISMISSAL'
  | 'PARTNER_CHURN_WEIGHT_ADJUSTMENT'
  | 'TRADE_COLLUSION_CONFIRMATION';

export interface FlywheelFeedbackSubmission {
  feedbackId: string;
  entityId: string;
  feedbackType: FlywheelFeedbackType;
  operatorId: string;
  originalPayload: Record<string, any>;
  correctedPayload: Record<string, any>;
  operatorRationale: string;
  submittedAt: string;
}

export interface FlywheelDiagnosticStatus {
  totalFeedbackEvents: number;
  uncalibratedDiscrepancies: number;
  shadowModelBrierScore: number;
  calibrationDriftDetected: boolean;
  lastRetrainingTimestamp: string;
}
```

---

### 1.10 Disaster Recovery, Chaos & Hardening Proofs (Feature 015)

```typescript
export interface DisasterRecoveryProof {
  runbookId: string;
  runbookName: string;
  lastExecutedTimestamp: string;
  verificationStatus: 'PASS' | 'FAIL';
  kmsKeyringRotationStatus: 'ACTIVE_ROTATED' | 'PENDING';
  backupCheckpointHash: string;
  warmStartCacheState: 'WARMED' | 'COLD' | 'REHYDRATING';
}

export interface RedLineGateStatus {
  gateId: 'RL-1' | 'RL-2' | 'RL-3' | 'RL-4' | 'RL-5' | 'RL-6' | 'RL-7';
  name: string;
  status: 'PASS' | 'FAIL';
  marginDelta: number;
  evaluatedOn: string;
}
```

---

### 1.11 Full-Stack API Bridge Payloads

```typescript
export interface WorkstationApiResponse {
  workstation: PersonaRole;
  isLiveConnected: boolean;
  isCachedFallback: boolean;
  fallbackReason?: string;
  asOfTimestamp: string;
  session: CockpitSession;
  triageItems: TriageItem[];
  activeDossier: CopilotDossier;
  canvasPayload: {
    type: 'CAUSAL_DAG' | 'TOPOLOGICAL_GRAPH' | 'CHURN_RADAR' | 'LEDGER_TIMELINE' | 'OPERATIONS_SLO';
    data: CausalDagPayload | TopologicalGraphPayload | PartnerChurnItem[] | LedgerAuditRecord[] | SloHealthItem[];
  };
  stagedActionCards: ActionIntentCard[];
  flywheelStatus?: FlywheelDiagnosticStatus;
  drProofs?: DisasterRecoveryProof[];
  redLineGates?: RedLineGateStatus[];
}
```

---

## 2. Validation Rules & State Transitions

1. **Attribution Sum Invariance**:
   $$\sum_{i=1}^n \text{AttributionWaterfallItem}_i.\text{percentageShare} = 100.0\% \pm 0.01\%$$
   The UI state manager asserts this invariant upon every parametric slider update. If violation occurs, an invariant error is raised.

2. **Causal Refuter Invariance (Principle III)**:
   An edge is labeled `VERIFIED_CAUSAL` strictly if:
   $$\text{confidence} \ge 0.80 \quad \text{AND} \quad \text{placeboRefuterPValue} > 0.05$$
   Otherwise, the edge must be styled with dashed amber strokes and explicitly labeled "correlation detected; insufficient evidence for causation".

3. **Four-Eyes Separation of Duty (Principle II)**:
   For any `ActionIntentCard` with `severity === 'HIGH'`:
   $$\text{secondOfficerId} \ne \text{initiatorOfficerId}$$
   The commit handler strictly blocks execution if only 1 approval signature exists.

4. **100% Metric Provenance Coverage (Principle I & V)**:
   No raw numerical string may appear in dossier cards or KPI panels without an attached `MetricProvenance` record providing `metricId`, `asOfTimestamp`, and `originEngine`.
