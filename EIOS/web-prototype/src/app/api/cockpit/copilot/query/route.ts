import { NextRequest, NextResponse } from 'next/server';
import { AnswerSource, CopilotQueryResponse } from '@/components/cockpit/state/cockpit-types';

import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import {
  assistantStatusOf,
  dataOriginOf,
  normalizeCitedMetric,
  normalizeProposal,
  normalizeSource,
  bundleIdOf,
  normalizeViewCommands,
} from '@/lib/server/normalize';

// A live Gemini turn with tool calls can take well over the default proxy timeout.
const COPILOT_TIMEOUT_MS = 90_000;

/**
 * Relay the backend's assistant answer. Every trust field comes from the backend: the status, each figure's source
 * and origin, and the proposals with the request that stages them. The assistant does not run the Metric Auditor, so
 * nothing here ever claims an audit pass. An answer without a readable status is refused, never guessed.
 */
export async function POST(req: NextRequest) {
  let body: Record<string, unknown> = {};
  try {
    body = await req.json();
  } catch {
    body = {};
  }
  const query = typeof body.query === 'string' ? body.query : '';

  const res = await callBackend(
    req,
    '/api/cockpit/copilot/query',
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
    { timeoutMs: COPILOT_TIMEOUT_MS },
  );
  if (!res) return backendUnavailable();
  if (!res.ok) return relayError(res);

  const data = await res.json().catch(() => null);
  if (!data || typeof data !== 'object') {
    return NextResponse.json({ detail: 'EIOS backend returned an unreadable copilot response' }, { status: 502 });
  }

  const rawCitations: Record<string, unknown>[] = Array.isArray(data.provenance_citations) ? data.provenance_citations : [];
  const assistantStatus = assistantStatusOf(data.assistant_status);
  if (!assistantStatus) {
    return NextResponse.json({ detail: 'EIOS backend returned an answer with no readable status' }, { status: 502 });
  }
  const rawProposals: Record<string, unknown>[] = Array.isArray(data.proposals) ? data.proposals : [];
  const rawSources: unknown[] = Array.isArray(data.sources) ? data.sources : [];

  const normalized: CopilotQueryResponse = {
    queryId: data.queryId ?? `qry_${Date.now()}`,
    naturalLanguageQuery: data.query || query,
    responseMarkdown: data.response ?? '',
    citedMetrics: rawCitations.map((m, idx) => normalizeCitedMetric(m, idx)),
    sources: rawSources.map(normalizeSource).filter((s): s is AnswerSource => s !== undefined),
    assistantStatus,
    blocked: data.blocked === true,
    blockReason: typeof data.block_reason === 'string' ? data.block_reason : undefined,
    dataOrigin: dataOriginOf(data.data_origin),
    steps: Array.isArray(data.steps) ? data.steps.filter((s: unknown): s is string => typeof s === 'string') : [],
    proposals: rawProposals.map(normalizeProposal).filter((p): p is NonNullable<typeof p> => p !== undefined),
    viewCommands: normalizeViewCommands(data.view_commands),
    evidenceBundleId: bundleIdOf(data.evidence_bundle_id),
    turnLatencyMs: typeof data.turn_latency_ms === 'number' ? data.turn_latency_ms : undefined,
    fallbackReason: typeof data.fallback_reason === 'string' ? data.fallback_reason : undefined,
    timestamp: data.timestamp ?? new Date().toISOString(),
  };
  return NextResponse.json(normalized);
}
