/**
 * TypeScript domain entities and interface contracts for the Institutional Operator Cockpit.
 * Governed by specs/016-cockpit-frontend/data-model.md and Constitution Principles I-VIII.
 */

export type PersonaRole =
  | 'executive'
  | 'aml_investigator'
  | 'partner_manager'
  | 'compliance_auditor'
  | 'data_operations';

export function normalizePersonaRole(raw: unknown): PersonaRole | null {
  if (typeof raw !== 'string') return null;
  const clean = raw.toLowerCase().trim().replace(/[-_]+$/, '');
  if (clean === 'executive' || clean === 'exec' || clean === 'ceo' || clean === 'cfo') return 'executive';
  if (clean === 'aml_investigator' || clean === 'aml' || clean === 'investigator' || clean === 'aml-investigator') return 'aml_investigator';
  if (clean === 'partner_manager' || clean === 'partner' || clean === 'partners' || clean === 'partner-manager' || clean === 'affiliate') return 'partner_manager';
  if (clean === 'compliance_auditor' || clean === 'compliance' || clean === 'audit' || clean === 'auditor' || clean === 'compliance-auditor') return 'compliance_auditor';
  if (clean === 'data_operations' || clean === 'data' || clean === 'data_platform' || clean === 'data-platform' || clean === 'operations' || clean === 'data-operations') return 'data_operations';
  return null;
}


export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type TriageStatus = 'OPEN' | 'INVESTIGATING' | 'STAGED' | 'RESOLVED' | 'DISMISSED';

export type ProvenanceCitation =
  | '[BRIEF]'
  | '[ASSUMPTION]'
  | '[ILLUSTRATIVE]'
  | '[TARGET]'
  | '[SPIKE]'
  | '[COMPUTED]';

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

/** Where a figure came from. Absent means the backend did not say, which is never shown as live. */
/** `engine`: computed by the engines over the seeded world; `fixture`: hand-written payloads. */
export type DataOrigin = 'live' | 'engine' | 'fixture';

export interface MetricProvenance {
  metricId: string;
  name: string;
  rawValue: number | string;
  formattedValue: string;
  unit?: string;
  semanticDefinitionVersion: string; // e.g. "v2.4.1 [d8a9f2]"
  asOfTimestamp: string; // ISO 8601
  originEngine: 'duckdb:semantic_layer' | 'bigquery:metrics_job' | 'realtime:flink' | 'offline:scm' | string;
  stewardRole: string; // e.g. "VP Finance", "Lead AML Officer"
  citation: ProvenanceCitation;
  isCached: boolean;
  /** Set by the backend for each figure of an assistant answer; absent for legacy citations. */
  dataOrigin?: DataOrigin;
}

export interface DossierSection {
  sectionId: string;
  title: string;
  narrativeText: string;
  citations: string[];
  metrics: MetricProvenance[];
  isFallbackReplay?: boolean;
}

export interface TradeOffCard {
  /** When present, staging this card goes through the backend with exactly this request. */
  stageRequest?: StageRequest;
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
  /** Absent when the backend computed no such ratio; never filled in. */
  netLossProfitRatio?: number;
  statutoryCitations: string[];
  /** Why `statutoryCitations` is empty, when it is. */
  statutoryNote?: string | null;
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

export interface WhatIfShockParameters {
  feeShockBps: number;
  churnRateDelta: number;
  complianceTighteningIndex: number;
  settlementDelayHours: number;
}

export type GraphNodeType = 'ACCOUNT' | 'DEVICE' | 'IP_ADDRESS' | 'PAYMENT_METHOD' | 'COLLAPSED_CLUSTER';
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
  /** Measured by the backend; absent when the edge carries no volume or date. */
  amountUsd?: number;
  dayIndex?: number;
}

export interface TopologicalGraphPayload {
  graphId: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  hubSuppressionThreshold: number; // degree >= 15 triggers suppression
  activeSuppressionCount: number;
}

export interface PartnerChurnItem {
  partnerId: string;
  name: string;
  tier: 'TIER_1_SUPER' | 'TIER_2_MASTER' | 'TIER_3_AFFILIATE';
  pChurn: number; // 0.00 to 1.00
  valueAtRiskUsd: number;
  daysToChurn: number;
  changePointDetected: boolean;
  /** Highest opposite-trading pair confidence across the partner's network (0..1); absent when not computed. */
  mirrorTradeCorrelation?: number;
  extractedCommissionUsd?: number;
  region?: string;
  cohort?: string;
  loginDecayPct?: number;
  referralDropWoWPct?: number;
  cashierLatencyHours?: number;
  supportTicketCount?: number;
  competitorPoaching?: string;
  primaryDriver?: 'OPERATIONAL_CASHIER' | 'COMPETITIVE_POACHING' | 'COMMERCIAL_REBATE' | 'CYCLICAL' | string;
  primaryRootCause?: string;
  projectedLiftPct?: number;
  netMarginRecoveryUsd?: number;
  empiricalPlaybookWinRate?: number;
  historicalDrift?: {
    tMinus30d: { pChurn: number; valueAtRiskUsd: number };
    tMinus14d: { pChurn: number; valueAtRiskUsd: number };
    driftVelocityPct: number;
  };
}

export interface WhatIfCausalResponse {
  partner_id: string;
  evaluator_model: string;
  evaluated_at: string;
  query_prompt: string;
  /** Relative drop in the scored hazard; null when no playbook applies. */
  projected_retention_lift_pct: number | null;
  /** The hazard model gives a point projection; no interval is claimed. */
  confidence_interval_95: [number, number] | null;
  estimated_deal_cost_usd: number | null;
  projected_net_margin_usd: number | null;
  verdict: 'NET_POSITIVE' | 'MARGIN_DILUTIVE' | 'NO_PLAYBOOK' | string;
  governed_decision_rationale: string;
  /** Null: a hazard-model projection is not a causal estimate (RL-3). */
  causal_refuter_p_value: number | null;
}

export interface CohortBatchProposal {
  cohortId: string;
  cohortName: string;
  partnerIds: string[];
  actionType: string;
  totalVaRProtectedUsd: number;
  kmsSignatureBadge: {
    keyId: string;
    algorithm: string;
    signatureDigest: string;
    verified: boolean;
  };
  stagedAt: string;
}

export interface PartnerHierarchyNode {
  partnerId: string;
  name: string;
  tierLevel: 1 | 2 | 3;
  monthlyCommissionUsd: number;
  subAffiliatesCount: number;
  children?: PartnerHierarchyNode[];
}

export type ActionIntentType =
  | 'HOLD_WITHDRAWAL'
  | 'LAUNCH_RETENTION_PLAYBOOK'
  | 'FREEZE_PARTNER_COMMISSION'
  | 'CLAWBACK_COMMISSION'
  | 'TUNE_MONITORING_THRESHOLD'
  | 'FILE_SAR_SUBMISSION'
  | 'DeployRetentionVIPDeal'
  | 'SuppressCGNATProxyCluster'
  | string;

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
  parameters: Record<string, unknown>;
  estimatedImpact: string;
  requiresFourEyes: boolean;
  kmsSignatureBadge: {
    keyId: string;
    algorithm: 'ECDSA_SHA256_P256' | 'ECDSA_P256_SHA256' | string;
    signatureDigest: string;
    verified: boolean;
  };
  fourEyesRecord: FourEyesApprovalRecord;
}

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

/** One decision-ledger entry as the auditor reads it (spec 032). */
export interface LedgerRow {
  ledgerSeq: number;
  eventType: string;
  entityId: string;
  actorId: string;
  previousHash: string;
  recordHash: string;
  timestamp: string;
  anchored: boolean;
}

export interface SignOff {
  officerId: string;
  role: string;
  approvedAt: string;
}

/** An intent and the human sign-offs it has so far; a pending intent has none. */
export interface IntentSignOffs {
  intentId: string;
  actionType: string;
  targetEntityId: string;
  severity: string;
  status: string;
  requiresDualApproval: boolean;
  first: SignOff | null;
  second: SignOff | null;
}

export interface SignedCheckpoint {
  checkpointId: string;
  chainHeadSeq: number;
  rootHash: string;
  retentionExpiration: string;
}

export interface ChainVerification {
  entriesVerified: number;
  unbroken: boolean;
  headHash: string;
  anchorsMatched: number;
}

export interface ComplianceLedger {
  entries: LedgerRow[];
  approvals: IntentSignOffs[];
  checkpoints: SignedCheckpoint[];
  verification: ChainVerification;
  isSimulated: boolean;
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

/**
 * What the ADK assistant says about its own answer. ASSEMBLED: every figure was filled in by the system from a
 * governed result of this turn (the Metric Auditor did not run). BLOCKED: screening stopped it. FAILED_CLOSED: it
 * could not support an answer and shows no figure. UNAVAILABLE: the model or data failed.
 */
export type AssistantStatus = 'ASSEMBLED' | 'BLOCKED' | 'FAILED_CLOSED' | 'UNAVAILABLE';

/** The request the stage endpoint takes, built by the backend so the browser never invents a vocabulary. */
export interface StageRequest {
  action_type: string;
  target_entity_id: string;
  severity: string;
  requires_four_eyes: boolean;
  metadata: Record<string, unknown>;
  /** The sealed evidence the hub signs with the intent (`evidence_refs`). */
  evidence_bundle_id?: string;
}

/** A draft the assistant proposes. It is never signed, staged or approved until a human stages it. */
export interface AssistantProposal {
  proposalRef: string;
  kind: string;
  label: string;
  offer: string;
  estimatedCostUsd: number;
  expectedEffectLow: number;
  expectedEffectHigh: number;
  expectedEffectBasis: string;
  approvalRequirement: string;
  signed: false;
  staged: false;
  dataOrigin?: DataOrigin;
  source: string;
  asOf: string;
  stageRequest: StageRequest;
}

/** A passage of a regulation the answer quoted: the document, where in it, and the text as the regulator wrote it. */
export interface AnswerSource {
  passageId: string;
  documentId: string;
  title: string;
  jurisdiction: string;
  pages: string;
  text: string;
  dataOrigin?: DataOrigin;
}

/** A map move the geospatial assistant made: an object a tool of the same turn returned, never coordinates. */
export interface ViewCommand {
  kind: 'country' | 'corridor' | 'mismatch' | 'gateway' | 'account';
  id: string;
}

export interface CopilotQueryResponse {
  queryId: string;
  naturalLanguageQuery: string;
  responseMarkdown: string;
  citedMetrics: MetricProvenance[];
  sources?: AnswerSource[];
  assistantStatus: AssistantStatus;
  blocked: boolean;
  blockReason?: string;
  dataOrigin?: DataOrigin;
  steps: string[];
  proposals: AssistantProposal[];
  /** Map moves the assembler accepted (geospatial workstation only); empty elsewhere. */
  viewCommands?: ViewCommand[];
  /** SHA-256 of the sealed evidence of a turn that proposed a hold or drafted a SAR; absent for any other turn. */
  evidenceBundleId?: string;
  turnLatencyMs?: number;
  fallbackReason?: string;
  timestamp: string;
}

export type FlywheelFeedbackType =
  | 'SAR_NARRATIVE_CORRECTION'
  | 'SAR_NARRATIVE_EDIT'
  | 'FALSE_POSITIVE_ALERT_DISMISSAL'
  | 'PARTNER_CHURN_WEIGHT_ADJUSTMENT'
  | 'TRADE_COLLUSION_CONFIRMATION';

export interface FlywheelFeedbackSubmission {
  feedbackId: string;
  entityId: string;
  feedbackType: FlywheelFeedbackType;
  operatorId: string;
  originalPayload: Record<string, unknown>;
  correctedPayload: Record<string, unknown>;
  operatorRationale: string;
  submittedAt: string;
}

export interface FlywheelDiagnosticStatus {
  totalFeedbackEvents: number;
  uncalibratedDiscrepancies: number | null; // null: nothing counts them on this plane
  shadowModelBrierScore: number | null;
  calibrationDriftDetected: boolean;
  lastRetrainingTimestamp: string | null;
}

export interface DisasterRecoveryProof {
  runbookId: string;
  runbookName: string;
  lastExecutedTimestamp: string;
  verificationStatus: 'PASS' | 'FAIL';
  kmsKeyringRotationStatus: 'ACTIVE_ROTATED' | 'PENDING' | 'VERIFIED_VALID' | string;
  backupCheckpointHash: string;
  warmStartCacheState: 'WARMED' | 'COLD' | 'REHYDRATING' | string;
  /** Set when the proof is a drill that was actually run: what it restored and how fast. */
  rowsExported?: number;
  rowsRestored?: number;
  restoreMs?: number;
}

export interface RedLineGateStatus {
  gateId: 'RL-1' | 'RL-2' | 'RL-3' | 'RL-4' | 'RL-5' | 'RL-6' | 'RL-7';
  name: string;
  status: 'PASS' | 'FAIL' | 'NOT_MEASURED';
  marginDelta: number | null;
  evaluatedOn: string;
  /** What was measured, or why nothing was. */
  basis?: string;
}

/** One account's computed dossier and canvas, fetched when the operator selects a case. */
export interface CaseApiResponse extends CaseExtras {
  entityId: string;
  dataOrigin: DataOrigin;
  activeDossier: CopilotDossier;
  canvasPayload: WorkstationApiResponse['canvasPayload'] | null;
}

/** One tile of the AML evidence strip: a computed figure with what it is measured against. */
export interface EvidenceTile {
  label: string;
  value: string;
  caption: string;
  tone: 'alert' | 'neutral';
}

export interface EvidenceStrip {
  title: string;
  severity: string;
  score: number | null;
  tiles: EvidenceTile[];
  metrics: MetricProvenance[];
}

/** Stage requests the hub understands for the selected account; null means the action does not apply to it. */
export interface CaseActions {
  hold: StageRequest | null;
  fileSar: StageRequest | null;
}

/** What the AML screen shows around a case's dossier when the data is engine-computed. */
export interface CaseExtras {
  evidenceStrip?: EvidenceStrip;
  sarDraft?: SarDraftDocument;
  caseActions?: CaseActions;
}

export interface WorkstationApiResponse extends CaseExtras {
  workstation: PersonaRole;
  isLiveConnected: boolean;
  isCachedFallback: boolean;
  /** Absent means fixture: a state is only 'live' when the backend says it came from governed data. */
  dataOrigin?: DataOrigin;
  fallbackReason?: string;
  asOfTimestamp: string;
  session: CockpitSession;
  triageItems: TriageItem[];
  activeDossier: CopilotDossier;
  canvasPayload: {
    type: 'CAUSAL_DAG' | 'TOPOLOGICAL_GRAPH' | 'CHURN_RADAR' | 'LEDGER_TIMELINE' | 'OPERATIONS_SLO';
    data: unknown;
  };
  stagedActionCards: ActionIntentCard[];
  flywheelStatus?: FlywheelDiagnosticStatus;
  drProofs?: DisasterRecoveryProof[];
  redLineGates?: RedLineGateStatus[];
}

/** The assistant's brief for an alert, prepared ahead of time (docs/ambient-dossiers.md). Same figures and sources as an answer. */
export interface PreparedBrief {
  entityId: string;
  preparedAt: string;
  expiresAt: string;
  /** Past its time to live: still shown, and said to be older. */
  stale: boolean;
  text: string;
  citedMetrics: MetricProvenance[];
  sources: AnswerSource[];
}
