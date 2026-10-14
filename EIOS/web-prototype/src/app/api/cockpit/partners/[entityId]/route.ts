import { NextRequest, NextResponse } from 'next/server';
import type { CaseApiResponse } from '@/components/cockpit/state/cockpit-types';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import { dataOriginOf, normalizeCanvas, normalizeDossier } from '@/lib/server/normalize';

/**
 * One partner's computed dossier, radar and referral network, for the partner an operator just selected.
 * An unreachable backend is a 503 and an unknown partner a 404: nothing here invents a dossier.
 */
export async function GET(req: NextRequest, context: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await context.params;
  const res = await callBackend(req, `/api/cockpit/partners/${encodeURIComponent(entityId)}`, {
    headers: { Accept: 'application/json' },
  });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);

  const raw = await res.json();
  const shape = getMockWorkstationState('partner_manager');
  const body: CaseApiResponse = {
    entityId: raw.entity_id ?? entityId,
    dataOrigin: dataOriginOf(raw.data_origin) ?? 'fixture',
    activeDossier: normalizeDossier(raw.active_dossier ?? {}, 'partner_manager', {
      ...shape.activeDossier,
      tradeOffs: undefined,
      sarDraft: undefined,
    }),
    canvasPayload: raw.kinetic_canvas ? normalizeCanvas(raw.kinetic_canvas, shape.canvasPayload) : null,
  };
  return NextResponse.json(body);
}
