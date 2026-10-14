import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import { normalizeLedger } from '@/lib/server/normalize-ledger';

/** The decision ledger the shelf writes to. An unreachable backend is a 503: nothing here invents an entry. */
export async function GET(req: NextRequest) {
  const res = await callBackend(req, '/api/cockpit/compliance/ledger', {
    headers: { Accept: 'application/json' },
  });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  return NextResponse.json(normalizeLedger(await res.json()));
}
