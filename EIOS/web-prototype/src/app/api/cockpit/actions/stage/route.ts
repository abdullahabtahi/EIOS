import { NextRequest } from 'next/server';
import { callBackend, relay } from '@/lib/server/backend';

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  return relay(
    await callBackend(req, '/api/cockpit/actions/stage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  );
}
