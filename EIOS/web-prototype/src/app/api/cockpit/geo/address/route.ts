import { NextRequest, NextResponse } from 'next/server';
import { callBackend, relay } from '@/lib/server/backend';

/**
 * What the network reference says about one IP address. A POST so the address is in the body and never in a URL; the
 * proxy neither logs nor keeps it. An outage is a 503 and a bad address a 422, relayed as they are.
 */
export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => null)) as { address?: unknown } | null;
  if (!body || typeof body.address !== 'string') {
    return NextResponse.json({ detail: 'not_an_ip_address' }, { status: 422 });
  }
  return relay(
    await callBackend(req, '/api/cockpit/geo/address', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address: body.address }),
    }),
  );
}
