import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';

/** Public reference layers for the map. An unreachable or unconfigured backend is a 503: nothing here invents a country. */
export async function GET(req: NextRequest) {
  const res = await callBackend(req, '/api/cockpit/geo/reference', {
    headers: { Accept: 'application/json' },
  }, { timeoutMs: 30_000 });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  return NextResponse.json(await res.json());
}
