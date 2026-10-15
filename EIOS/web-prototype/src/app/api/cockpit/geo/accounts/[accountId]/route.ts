import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';

/** One account's geography as case evidence. Unknown account is a 404 and an outage a 503; nothing is invented here. */
export async function GET(req: NextRequest, context: { params: Promise<{ accountId: string }> }) {
  const { accountId } = await context.params;
  const res = await callBackend(req, `/api/cockpit/geo/accounts/${encodeURIComponent(accountId)}`, {
    headers: { Accept: 'application/json' },
  }, { timeoutMs: 60_000 });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  return NextResponse.json(await res.json());
}
