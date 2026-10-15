import { NextRequest } from 'next/server';
import { callBackend, relay } from '@/lib/server/backend';

/** The models the operator may pick for the assistant (key, label, note, default). The backend decides; ids never reach the browser. */
export async function GET(req: NextRequest) {
  return relay(await callBackend(req, '/api/cockpit/copilot/models'));
}
