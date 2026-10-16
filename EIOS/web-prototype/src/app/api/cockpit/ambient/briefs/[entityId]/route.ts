import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import { normalizeBrief } from '@/lib/server/normalize';

/**
 * The brief the assistant prepared ahead of time for an alert. No brief is a 404 the dossier says plainly; an outage is
 * a 503. A body that is not a brief (no entity, text or time) is a 502, never an empty card.
 */
export async function GET(req: NextRequest, context: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await context.params;
  const res = await callBackend(req, `/api/cockpit/ambient/briefs/${encodeURIComponent(entityId)}`, {
    headers: { Accept: 'application/json' },
  });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  const brief = normalizeBrief(await res.json());
  if (!brief) return NextResponse.json({ detail: 'the brief was not readable' }, { status: 502 });
  return NextResponse.json(brief);
}
