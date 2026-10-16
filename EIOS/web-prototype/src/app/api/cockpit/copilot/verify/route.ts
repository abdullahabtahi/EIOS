import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';

/**
 * Relay a replay of an answer's figures. The backend derives each figure again through the governed port and says
 * whether it matches; this route adds nothing and relays the backend's status, so an outage is never a pass.
 */
export async function POST(req: NextRequest) {
  const body = await req.text();
  const res = await callBackend(
    req,
    '/api/cockpit/copilot/verify',
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body },
    { timeoutMs: 60_000 },
  );
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  return NextResponse.json(await res.json());
}
