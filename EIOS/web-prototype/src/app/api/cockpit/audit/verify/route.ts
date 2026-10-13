import { NextRequest } from 'next/server';
import { callBackend, relay } from '@/lib/server/backend';

export async function GET(req: NextRequest) {
  return relay(await callBackend(req, '/api/cockpit/audit/verify', { headers: { Accept: 'application/json' } }));
}

export async function POST(req: NextRequest) {
  return GET(req);
}
