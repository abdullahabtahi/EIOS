import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';

/** Customer flows from the geo engine. The first call builds the engine's view, so it gets a longer budget; an outage is a 503. */
export async function GET(req: NextRequest) {
  const res = await callBackend(req, '/api/cockpit/geo/flows', {
    headers: { Accept: 'application/json' },
  }, { timeoutMs: 60_000 });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  return NextResponse.json(await res.json());
}
