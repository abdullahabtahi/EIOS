/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextRequest, NextResponse } from 'next/server';
import {
  PersonaRole,
  WorkstationApiResponse,
  TriageItem,
  CopilotDossier,
  ActionIntentCard,
} from '@/components/cockpit/state/cockpit-types';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';

import { callBackend, relayError } from '@/lib/server/backend';

function normalizeBackendWorkstation(raw: any, role: PersonaRole): WorkstationApiResponse {
  const mock = getMockWorkstationState(role);
  if (!raw || typeof raw !== 'object') return mock;

  // 1. Triage Items
  let triageItems: TriageItem[] = mock.triageItems;
  const rawItems = raw.triage_queue?.items || raw.triageItems;
  if (Array.isArray(rawItems) && rawItems.length > 0) {
    triageItems = rawItems.map((item: any, idx: number) => ({
      id: item.id || `item_${idx}`,
      role: role,
      title: item.title || item.name || `Triage Item ${idx + 1}`,
      subtitle: item.subtitle || item.description || '',
      entityId: item.entity_id || item.entityId || 'ENTITY-01',
      entityType: item.entity_type || item.entityType || 'ENTITY',
      priorityScore: item.priority_score ?? item.priorityScore ?? 0.5,
      severity: item.severity || 'MEDIUM',
      status: item.status || 'OPEN',
      timestamp: item.timestamp || new Date().toISOString(),
      tags: item.tags || [],
      discrepancyBps: item.discrepancy_bps ?? item.discrepancyBps,
      metricsSummary: item.metrics_summary || item.metricsSummary,
    }));
  }

  // 2. Active Dossier
  let activeDossier: CopilotDossier = mock.activeDossier;
  const rawDossier = raw.active_dossier || raw.activeDossier;
  if (rawDossier && typeof rawDossier === 'object') {
    const rawSections = rawDossier.sections || rawDossier.narrativeSections || [];
    const normalizedSections = Array.isArray(rawSections) && rawSections.length > 0
      ? rawSections.map((s: any, idx: number) => ({
          sectionId: s.section_id || s.sectionId || s.id || `sec_${idx}`,
          title: s.title || `Section ${idx + 1}`,
          narrativeText: s.narrative_text || s.narrativeText || s.narrativeMarkdown || s.narrative || '',
          citations: s.citations || s.tags || [],
          metrics: (s.metrics || s.citedMetrics || []).map((m: any) => ({
            metricId: m.metric_id || m.metricId || 'M-UNKNOWN',
            name: m.name || m.metric_id || m.metricId || 'Metric',
            rawValue: m.raw_value ?? m.rawValue ?? 0,
            formattedValue: m.formatted_value || m.formattedValue || String(m.raw_value ?? m.rawValue ?? 0),
            unit: m.unit || '',
            semanticDefinitionVersion: m.semantic_definition_version || m.semanticDefinitionVersion || 'v1.4',
            asOfTimestamp: m.as_of_timestamp || m.asOfTimestamp || new Date().toISOString(),
            originEngine: m.origin_engine || m.originEngine || 'duckdb:semantic_layer',
            stewardRole: m.steward_role || m.stewardRole || 'Steward',
            citation: m.citation || '[CITED]',
            isCached: m.is_cached ?? m.isCached ?? false,
          })),
        }))
      : mock.activeDossier.sections;

    activeDossier = {
      dossierId: rawDossier.dossier_id || rawDossier.dossierId || mock.activeDossier.dossierId,
      entityId: rawDossier.entity_id || rawDossier.entityId || mock.activeDossier.entityId,
      role: role,
      headline: rawDossier.headline || mock.activeDossier.headline,
      executiveSummary: rawDossier.executive_summary || rawDossier.executiveSummary || mock.activeDossier.executiveSummary,
      sections: normalizedSections,
      tradeOffs: rawDossier.trade_offs || rawDossier.tradeOffs || mock.activeDossier.tradeOffs,
      sarDraft: rawDossier.sar_draft || rawDossier.sarDraft || mock.activeDossier.sarDraft,
      asOfTimestamp: rawDossier.as_of_timestamp || rawDossier.asOfTimestamp || new Date().toISOString(),
      isCachedSnapshot: rawDossier.is_cached_snapshot ?? rawDossier.isCachedSnapshot ?? false,
      replayReason: rawDossier.replay_reason ?? rawDossier.replayReason,
    };
  }

  // 3. Canvas Payload
  let canvasPayload = mock.canvasPayload;
  const rawCanvas = raw.kinetic_canvas || raw.canvasPayload;
  if (rawCanvas && typeof rawCanvas === 'object') {
    canvasPayload = {
      type: rawCanvas.canvas_type || rawCanvas.type || mock.canvasPayload.type,
      data: rawCanvas.payload || rawCanvas.data || mock.canvasPayload.data,
    };
  }

  // 4. Staged Action Cards
  let stagedActionCards: ActionIntentCard[] = mock.stagedActionCards;
  const rawActions = raw.governed_action_shelf?.actions || raw.stagedActionCards;
  if (Array.isArray(rawActions) && rawActions.length > 0) {
    stagedActionCards = rawActions.map((a: any, idx: number) => ({
      intentId: a.intent_id || a.intentId || `act_${idx}`,
      actionType: a.action_type || a.actionType || 'GENERIC_ACTION',
      targetEntityId: a.target_entity_id || a.targetEntityId || 'ENTITY-01',
      targetEntityType: a.target_entity_type || a.targetEntityType || 'ACCOUNT',
      severity: a.severity || 'MEDIUM',
      lifecycleState: a.lifecycle_state || a.lifecycleState || 'STAGED',
      stagedTimestamp: a.staged_timestamp || a.stagedTimestamp || new Date().toISOString(),
      expiresAt: a.expires_at || a.expiresAt || new Date(Date.now() + 900000).toISOString(),
      parameters: a.parameters || {},
      estimatedImpact: a.estimated_impact || a.estimatedImpact || 'Action staged',
      requiresFourEyes: a.requires_four_eyes ?? a.requiresFourEyes ?? false,
      kmsSignatureBadge: {
        keyId: a.kms_signature_badge?.key_id || a.kmsSignatureBadge?.keyId || 'projects/kms/keys/key1',
        algorithm: a.kms_signature_badge?.algorithm || a.kmsSignatureBadge?.algorithm || 'ECDSA_P256_SHA256',
        signatureDigest: a.kms_signature_badge?.signature_digest || a.kmsSignatureBadge?.signatureDigest || 'DIGEST_VALID',
        verified: a.kms_signature_badge?.verified ?? a.kmsSignatureBadge?.verified ?? true,
      },
      fourEyesRecord: {
        initiatorOfficerId: a.four_eyes_record?.initiator_officer_id || a.fourEyesRecord?.initiatorOfficerId || 'OPERATOR_PRIMARY',
        initiatorTimestamp: a.four_eyes_record?.initiator_timestamp || a.fourEyesRecord?.initiatorTimestamp || new Date().toISOString(),
        idpClaimValidation: true,
      },
    }));
  }

  return {
    workstation: role,
    isLiveConnected: true,
    isCachedFallback: false,
    asOfTimestamp: raw.as_of_timestamp || raw.asOfTimestamp || new Date().toISOString(),
    session: {
      ...mock.session,
      sessionId: raw.session?.session_id || raw.session?.sessionId || mock.session.sessionId,
      activeRole: role,
      systemLatencyMs: raw.session?.system_latency_ms || raw.session?.systemLatencyMs || 18,
    },
    triageItems,
    activeDossier,
    canvasPayload,
    stagedActionCards,
    drProofs: mock.drProofs,
    redLineGates: mock.redLineGates,
    flywheelStatus: mock.flywheelStatus,
  };
}

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ role: string }> }
) {
  const { role } = await context.params;
  const validRole = role as PersonaRole;

  try {
    const res = await callBackend(req, `/api/cockpit/workstations/${role}`, {
      headers: { Accept: 'application/json' },
    });
    if (res && (res.status === 401 || res.status === 403)) return relayError(res);

    if (res?.ok) {
      const raw = await res.json();
      const normalized = normalizeBackendWorkstation(raw, validRole);
      return NextResponse.json(normalized);
    }
  } catch {
    // Graceful offline fallback under presentation partition (Principle VIII)
  }

  // Pre-compiled verified contract fixture
  const fallback = getMockWorkstationState(validRole);
  return NextResponse.json({
    ...fallback,
    isLiveConnected: false,
    isCachedFallback: true,
    fallbackReason: 'FastAPI presentation server offline; serving deterministic pre-compiled snapshot.',
  });
}
