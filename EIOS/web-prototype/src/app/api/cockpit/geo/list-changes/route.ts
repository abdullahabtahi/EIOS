import { NextRequest, NextResponse } from 'next/server';
import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';

const LISTS = new Set(['fatf', 'eu']);

/**
 * What the latest change of a published list does to this book. Only the two lists the backend knows are forwarded;
 * anything else is refused here. The first call may build the engine's view, so it gets the flows route's budget.
 */
export async function GET(req: NextRequest) {
  const listId = req.nextUrl.searchParams.get('list_id') ?? 'fatf';
  if (!LISTS.has(listId)) {
    return NextResponse.json({ detail: 'unknown_list' }, { status: 422 });
  }
  const res = await callBackend(
    req,
    `/api/cockpit/geo/list-changes?list_id=${listId}`,
    { headers: { Accept: 'application/json' } },
    { timeoutMs: 60_000 },
  );
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);
  return NextResponse.json(await res.json());
}
