import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import { normalizeActionCard } from '@/lib/server/normalize';

/**
 * The governed action shelf on its own. Never cached anywhere: it is what an approver acts on, so every call reads
 * the backend. An unreachable backend is a 503; nothing here fills in a card.
 */
export async function GET(req: NextRequest) {
  const res = await callBackend(req, '/api/cockpit/shelf', { headers: { Accept: 'application/json' } });
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  const raw = await res.json();
  const actions: Record<string, unknown>[] = Array.isArray(raw?.governed_action_shelf?.actions) ? raw.governed_action_shelf.actions : [];
  const stagedActionCards = actions.map(normalizeActionCard).filter((card) => card.intentId !== '');
  return NextResponse.json({ stagedActionCards }, { headers: { 'Cache-Control': 'no-store' } });
}
