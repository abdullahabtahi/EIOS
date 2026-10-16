import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import { bundleIdOf } from '@/lib/server/normalize';

/**
 * Replay a sealed evidence bundle: the backend asks every recorded call again through the governed port and compares
 * figure by figure. This route checks the id's shape and relays the backend's answer and status; an outage is never a
 * pass.
 */
export async function POST(req: NextRequest, context: { params: Promise<{ bundleId: string }> }) {
  const bundleId = bundleIdOf((await context.params).bundleId);
  if (!bundleId) return NextResponse.json({ detail: 'a bundle id is 64 lowercase hex characters' }, { status: 422 });
  const res = await callBackend(
    req,
    `/api/cockpit/evidence/${bundleId}/replay`,
    { method: 'POST' },
    { timeoutMs: 60_000 },
  );
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  return NextResponse.json(await res.json());
}
