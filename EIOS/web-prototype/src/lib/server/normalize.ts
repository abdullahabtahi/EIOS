/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Backend (snake_case) to cockpit (camelCase) normalizers shared by the proxy routes.
 *
 * Trust fields fail closed: a signature is `verified` only when the backend said `verified: true`
 * about a signature it actually carried. Nothing here invents a key id, a digest, a signer identity or
 * an identity-provider validation. Missing means empty / false, never a plausible-looking default.
 */
import type { ActionIntentCard, MetricProvenance, ProvenanceCitation } from '@/components/cockpit/state/cockpit-types';

type Raw = Record<string, any>;

const text = (value: unknown, fallback = ''): string => (typeof value === 'string' ? value : fallback);

const PROVENANCE_LABELS: readonly ProvenanceCitation[] = ['[BRIEF]', '[ASSUMPTION]', '[ILLUSTRATIVE]', '[TARGET]', '[SPIKE]'];

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

/** Normalize the backend's copilot citation rows. The as-of is the one the engine recorded. */
export function normalizeCitedMetric(raw: Raw, index: number): MetricProvenance {
  return {
    metricId: text(raw.metricId ?? raw.metric_id, `M-COPILOT-${index + 1}`),
    name: text(raw.name ?? raw.metric_id, 'Canonical Metric'),
    rawValue: Number(raw.rawValue ?? raw.raw_value ?? 0),
    formattedValue: text(raw.formattedValue ?? raw.formatted_value, String(raw.rawValue ?? raw.raw_value ?? '')),
    unit: text(raw.unit),
    semanticDefinitionVersion: text(raw.semanticDefinitionVersion ?? raw.semantic_definition_version),
    asOfTimestamp: text(raw.asOfTimestamp ?? raw.as_of),
    originEngine: text(raw.originEngine ?? raw.origin_engine ?? raw.steward),
    stewardRole: text(raw.stewardRole ?? raw.steward),
    citation: provenanceLabel(raw.citation),
    isCached: false,
  };
}
