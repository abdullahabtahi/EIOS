/* eslint-disable @typescript-eslint/no-explicit-any */
import { NextRequest, NextResponse } from 'next/server';
import {
  PersonaRole,
  WorkstationApiResponse,
  TriageItem,
  CopilotDossier,
  ActionIntentCard,
  DataOrigin,
} from '@/components/cockpit/state/cockpit-types';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';

import { callBackend, relayError } from '@/lib/server/backend';
import { normalizeActionCard, normalizeCanvas, normalizeCaseExtras, normalizeDossier } from '@/lib/server/normalize';

/** The backend labels its own data. Anything but an explicit [LIVE] or [ENGINE] badge is treated as fixture. */
function originOfBadge(badge: unknown): DataOrigin {
  if (badge === '[LIVE]') return 'live';
  if (badge === '[ENGINE]') return 'engine';
  return 'fixture';
}

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
  const origin = originOfBadge(raw.fallback_state?.badge_label);
  // An engine-computed case never borrows the fixture's trade-offs or SAR block: absent means none.
  const shape: CopilotDossier =
    origin === 'engine' ? { ...mock.activeDossier, tradeOffs: undefined, sarDraft: undefined } : mock.activeDossier;
  const rawDossier = raw.active_dossier || raw.activeDossier;
  const activeDossier: CopilotDossier =
    rawDossier && typeof rawDossier === 'object' ? normalizeDossier(rawDossier, role, shape) : shape;

  // 3. Canvas Payload
  const canvasPayload = normalizeCanvas(raw.kinetic_canvas || raw.canvasPayload, mock.canvasPayload);

  // 4. Staged Action Cards: signature state comes from the backend verdict, never a default
  let stagedActionCards: ActionIntentCard[] = mock.stagedActionCards;
  const rawActions = raw.governed_action_shelf?.actions || raw.stagedActionCards;
  if (Array.isArray(rawActions) && rawActions.length > 0) {
    stagedActionCards = rawActions.map(normalizeActionCard).filter((card) => card.intentId !== '');
  }

  return {
    workstation: role,
    isLiveConnected: true,
    isCachedFallback: false,
    // The backend labels its own data; anything but an explicit [LIVE] badge is treated as fixture.
    dataOrigin: origin,
    ...(origin === 'engine' ? normalizeCaseExtras(raw) : {}),
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
    const entityId = new URL(req.url).searchParams.get('entity_id');
    const query = entityId ? `?entity_id=${encodeURIComponent(entityId)}` : '';
    const res = await callBackend(req, `/api/cockpit/workstations/${role}${query}`, {
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
