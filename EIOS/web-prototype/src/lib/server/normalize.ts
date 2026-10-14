/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Backend (snake_case) to cockpit (camelCase) normalizers shared by the proxy routes.
 *
 * Trust fields fail closed: a signature is `verified` only when the backend said `verified: true`
 * about a signature it actually carried. Nothing here invents a key id, a digest, a signer identity or
 * an identity-provider validation. Missing means empty / false, never a plausible-looking default.
 */
import type {
  ActionIntentCard,
  AssistantProposal,
  AssistantStatus,
  CaseExtras,
  CopilotDossier,
  DataOrigin,
  MetricProvenance,
  PersonaRole,
  ProvenanceCitation,
  SarDraftDocument,
  StageRequest,
  WorkstationApiResponse,
} from '@/components/cockpit/state/cockpit-types';

type Raw = Record<string, any>;

const text = (value: unknown, fallback = ''): string => (typeof value === 'string' ? value : fallback);

const PROVENANCE_LABELS: readonly ProvenanceCitation[] = [
  '[BRIEF]',
  '[ASSUMPTION]',
  '[ILLUSTRATIVE]',
  '[TARGET]',
  '[SPIKE]',
  '[COMPUTED]',
];

/** A citation without a recognised regime label does not claim a source: it is shown as [ILLUSTRATIVE]. */
const provenanceLabel = (value: unknown): ProvenanceCitation =>
  PROVENANCE_LABELS.find((label) => label === value) ?? '[ILLUSTRATIVE]';

/** Normalize one backend governed-action card. Callers drop a card whose `intentId` is empty: it cannot be acted on. */
export function normalizeActionCard(raw: Raw): ActionIntentCard {
  const signature: Raw = raw.kms_signature ?? raw.kms_signature_badge ?? {};
  const fourEyes: Raw = raw.four_eyes_record ?? {};
  return {
    intentId: text(raw.intent_id ?? raw.intentId),
    actionType: text(raw.action_type ?? raw.actionType, 'UNKNOWN') as ActionIntentCard['actionType'],
    targetEntityId: text(raw.target_entity_id ?? raw.targetEntityId),
    targetEntityType: text(raw.target_entity_type ?? raw.targetEntityType, 'UNKNOWN'),
    severity: text(raw.severity, 'MEDIUM') as ActionIntentCard['severity'],
    lifecycleState: text(raw.lifecycle_state ?? raw.lifecycleState, 'STAGED') as ActionIntentCard['lifecycleState'],
    stagedTimestamp: text(raw.staged_timestamp ?? raw.stagedTimestamp),
    expiresAt: text(raw.expires_at ?? raw.expiresAt),
    parameters: raw.parameters ?? {},
    estimatedImpact: text(raw.estimated_impact ?? raw.estimatedImpact),
    requiresFourEyes: raw.requires_four_eyes ?? raw.requiresFourEyes ?? false,
    kmsSignatureBadge: {
      keyId: text(signature.key_id),
      algorithm: text(signature.algorithm),
      signatureDigest: text(signature.signature_digest),
      verified: signature.verified === true,
    },
    fourEyesRecord: {
      initiatorOfficerId: text(raw.initiator_officer_id ?? fourEyes.initiator_officer_id),
      initiatorTimestamp: text(fourEyes.initiator_timestamp),
      secondOfficerId: raw.second_officer_id ?? fourEyes.second_officer_id ?? undefined,
      idpClaimValidation: fourEyes.idp_claim_validation === true,
    },
  };
}

/** Live only when the backend says so; anything else the backend sends is unknown, never "live". */
export const dataOriginOf = (value: unknown): DataOrigin | undefined =>
  value === 'live' || value === 'engine' || value === 'fixture' ? value : undefined;

const ASSISTANT_STATUSES: readonly AssistantStatus[] = ['ASSEMBLED', 'BLOCKED', 'FAILED_CLOSED', 'UNAVAILABLE'];

/** An unknown status is dropped, so the browser falls back to the legacy audit reading instead of guessing. */
export const assistantStatusOf = (value: unknown): AssistantStatus | undefined =>
  ASSISTANT_STATUSES.find((status) => status === value);

const number = (value: unknown): number => (typeof value === 'number' && Number.isFinite(value) ? value : 0);

function stageRequestOf(raw: unknown): StageRequest | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const r = raw as Raw;
  if (typeof r.action_type !== 'string' || !r.action_type || typeof r.target_entity_id !== 'string' || !r.target_entity_id) {
    return undefined;
  }
  return {
    action_type: r.action_type,
    target_entity_id: r.target_entity_id,
    severity: text(r.severity, 'HIGH'),
    requires_four_eyes: r.requires_four_eyes !== false,
    metadata: r.metadata && typeof r.metadata === 'object' ? (r.metadata as Record<string, unknown>) : {},
  };
}

/** Normalize one assistant proposal. A proposal without a usable stage request cannot be acted on, so it is dropped. */
export function normalizeProposal(raw: Raw): AssistantProposal | undefined {
  const stageRequest = stageRequestOf(raw.stage_request);
  if (!stageRequest) return undefined;
  return {
    proposalRef: text(raw.proposal_ref),
    kind: text(raw.kind),
    label: text(raw.label),
    offer: text(raw.offer),
    estimatedCostUsd: number(raw.estimated_cost_usd),
    expectedEffectLow: number(raw.expected_effect_low),
    expectedEffectHigh: number(raw.expected_effect_high),
    expectedEffectBasis: text(raw.expected_effect_basis),
    approvalRequirement: text(raw.approval_requirement),
    signed: false,
    staged: false,
    dataOrigin: dataOriginOf(raw.data_origin),
    source: text(raw.source),
    asOf: text(raw.as_of),
    stageRequest,
  };
}

/** "partner.signals:PTR-723:days_to_intervention_deadline" reads "days to intervention deadline". */
export function metricLabel(id: string): string {
  if (!/[:._[\]]/.test(id)) return id;
  const last = id.split(':').pop()!.split('.').pop()!;
  return last.replace(/\[\d*\]/g, '').replace(/_(usd|pct)$/i, '').replace(/_/g, ' ').trim() || id;
}

/** Normalize the backend's copilot citation rows. The as-of is the one the engine recorded. */
export function normalizeCitedMetric(raw: Raw, index: number): MetricProvenance {
  return {
    metricId: text(raw.metricId ?? raw.metric_id, `M-COPILOT-${index + 1}`),
    name: metricLabel(text(raw.name ?? raw.metric_id, 'Canonical Metric')),
    rawValue: Number(raw.rawValue ?? raw.raw_value ?? 0),
    formattedValue: text(raw.formattedValue ?? raw.formatted_value, String(raw.rawValue ?? raw.raw_value ?? '')),
    unit: text(raw.unit),
    semanticDefinitionVersion: text(raw.semanticDefinitionVersion ?? raw.semantic_definition_version),
    asOfTimestamp: text(raw.asOfTimestamp ?? raw.as_of),
    originEngine: text(raw.originEngine ?? raw.origin_engine ?? raw.source ?? raw.steward),
    stewardRole: text(raw.stewardRole ?? raw.steward),
    citation: provenanceLabel(raw.citation),
    isCached: false,
    dataOrigin: dataOriginOf(raw.data_origin),
  };
}

/** One cited figure in cockpit shape; a field the backend left out gets a neutral default, never a claim. */
export function normalizeMetric(m: Raw): MetricProvenance {
  return {
    metricId: m.metric_id || m.metricId || 'M-UNKNOWN',
    name: m.name || m.metric_id || m.metricId || 'Metric',
    rawValue: m.raw_value ?? m.rawValue ?? 0,
    formattedValue: m.formatted_value || m.formattedValue || String(m.raw_value ?? m.rawValue ?? 0),
    unit: m.unit || '',
    semanticDefinitionVersion: m.semantic_definition_version || m.semanticDefinitionVersion || 'v1.4',
    asOfTimestamp: m.as_of_timestamp || m.asOfTimestamp || new Date().toISOString(),
    originEngine: m.origin_engine || m.originEngine || 'duckdb:semantic_layer',
    stewardRole: m.steward_role || m.stewardRole || 'Steward',
    citation: provenanceLabel(m.citation),
    isCached: m.is_cached ?? m.isCached ?? false,
    dataOrigin: dataOriginOf(m.data_origin),
  };
}

/** What the AML screen shows around a case, from an engine-backed response. Absent parts stay absent. */
export function normalizeCaseExtras(raw: Raw): CaseExtras {
  const strip: Raw | undefined = raw.evidence_strip;
  const actions: Raw | undefined = raw.case_actions;
  return {
    evidenceStrip: strip
      ? {
          title: text(strip.title),
          severity: text(strip.severity, 'NONE'),
          score: typeof strip.score === 'number' ? strip.score : null,
          tiles: Array.isArray(strip.tiles) ? strip.tiles : [],
          metrics: Array.isArray(strip.metrics) ? strip.metrics.map(normalizeMetric) : [],
        }
      : undefined,
    sarDraft: raw.sar_draft && typeof raw.sar_draft === 'object' ? (raw.sar_draft as SarDraftDocument) : undefined,
    caseActions: actions
      ? { hold: (actions.hold as StageRequest | null) ?? null, fileSar: (actions.file_sar as StageRequest | null) ?? null }
      : undefined,
  };
}

/**
 * A backend dossier in cockpit shape. A field the backend did not send keeps the fallback's value, so a partial
 * payload still renders; `sections` fall back only when the backend sent none.
 */
export function normalizeDossier(rawDossier: Raw, role: PersonaRole, fallback: CopilotDossier): CopilotDossier {
  const rawSections = rawDossier.sections || rawDossier.narrativeSections || [];
  const sections =
    Array.isArray(rawSections) && rawSections.length > 0
      ? rawSections.map((s: Raw, idx: number) => ({
          sectionId: s.section_id || s.sectionId || s.id || `sec_${idx}`,
          title: s.title || `Section ${idx + 1}`,
          narrativeText: s.narrative_text || s.narrativeText || s.narrativeMarkdown || s.narrative || '',
          citations: s.citations || s.tags || [],
          metrics: (s.metrics || s.citedMetrics || []).map(normalizeMetric),
        }))
      : fallback.sections;
  return {
    dossierId: rawDossier.dossier_id || rawDossier.dossierId || fallback.dossierId,
    entityId: rawDossier.entity_id || rawDossier.entityId || fallback.entityId,
    role,
    headline: rawDossier.headline || fallback.headline,
    executiveSummary: rawDossier.executive_summary || rawDossier.executiveSummary || fallback.executiveSummary,
    sections,
    tradeOffs: rawDossier.trade_offs || rawDossier.tradeOffs || fallback.tradeOffs,
    sarDraft: rawDossier.sar_draft || rawDossier.sarDraft || fallback.sarDraft,
    asOfTimestamp: rawDossier.as_of_timestamp || rawDossier.asOfTimestamp || new Date().toISOString(),
    isCachedSnapshot: rawDossier.is_cached_snapshot ?? rawDossier.isCachedSnapshot ?? false,
    replayReason: rawDossier.replay_reason ?? rawDossier.replayReason,
  };
}

/** The canvas the backend chose for the selection, or the fallback's when it chose none. */
export function normalizeCanvas(
  rawCanvas: Raw | null | undefined,
  fallback: WorkstationApiResponse['canvasPayload'],
): WorkstationApiResponse['canvasPayload'] {
  if (!rawCanvas || typeof rawCanvas !== 'object') return fallback;
  return {
    type: rawCanvas.canvas_type || rawCanvas.type || fallback.type,
    data: rawCanvas.payload || rawCanvas.data || fallback.data,
  };
}
