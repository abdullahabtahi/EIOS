import { NextRequest, NextResponse } from 'next/server';
import type { CaseApiResponse } from '@/components/cockpit/state/cockpit-types';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import { dataOriginOf, normalizeCanvas, normalizeCaseExtras, normalizeDossier } from '@/lib/server/normalize';

/**
 * One account's computed dossier and network canvas, for the case an operator just selected.
 * An unreachable backend is a 503 and an unknown account a 404: nothing here invents a dossier.
 */
export async function GET(req: NextRequest, context: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await context.params;
  const res = await callBackend(req, `/api/cockpit/aml/cases/${encodeURIComponent(entityId)}`, {
    headers: { Accept: 'application/json' },
  });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);

  const raw = await res.json();
  const shape = getMockWorkstationState('aml_investigator');
  const body: CaseApiResponse = {
    entityId: raw.entity_id ?? entityId,
    dataOrigin: dataOriginOf(raw.data_origin) ?? 'fixture',
    activeDossier: normalizeDossier(raw.active_dossier ?? {}, 'aml_investigator', {
      ...shape.activeDossier,
      tradeOffs: undefined,
      sarDraft: undefined,
    }),
    canvasPayload: raw.kinetic_canvas ? normalizeCanvas(raw.kinetic_canvas, shape.canvasPayload) : null,
    ...normalizeCaseExtras(raw),
  };
  return NextResponse.json(body);
}
