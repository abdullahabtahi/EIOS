import { NextRequest, NextResponse } from 'next/server';
import { CopilotQueryResponse } from '@/components/cockpit/state/cockpit-types';

import { backendUnavailable, callBackend, relayError } from '@/lib/server/backend';
import { normalizeActionCard, normalizeCitedMetric } from '@/lib/server/normalize';

// A live Gemini turn with tool calls can take well over the default proxy timeout.
const COPILOT_TIMEOUT_MS = 90_000;

/**
 * Relay the backend's copilot answer. Every trust field comes from the backend: the audit verdict, the
 * anchored numbers, the tool-trace count, the replay flag and the signature on a suggested action.
 * A missing or UNAUDITED audit is a failed audit.
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

  const audit = data.audit_record ?? {};
  const auditPassed = data.auditor_status === 'PASS' && audit.passed === true;
  const anchored: (number | string)[] = Array.isArray(audit.anchored_numbers) ? audit.anchored_numbers : [];
  const untraceable: (number | string)[] = Array.isArray(audit.unanchored_tokens) ? audit.unanchored_tokens : [];

  const rawCitations: Record<string, unknown>[] = Array.isArray(data.provenance_citations) ? data.provenance_citations : [];
  const rawAction = data.suggested_action;
  const suggestedAction = rawAction ? normalizeActionCard(rawAction) : undefined;

  const normalized: CopilotQueryResponse = {
    queryId: data.queryId ?? `qry_${Date.now()}`,
    naturalLanguageQuery: data.query || query,
    responseMarkdown: data.response ?? '',
    citedMetrics: rawCitations.map(normalizeCitedMetric),
    auditorResult: {
      auditPassed,
      extractedNumbers: [...anchored, ...untraceable],
      anchoredNumbers: anchored,
      untraceableNumbers: untraceable,
      toolTracesCount: Number(data.tool_trace_count ?? 0),
      rejectionReason: auditPassed
        ? undefined
        : untraceable.length > 0
          ? 'Ungrounded metric tokens detected without semantic tool trace.'
          : 'No passing Metric Auditor verdict accompanied this answer.',
    },
    suggestedAction: suggestedAction?.intentId ? suggestedAction : undefined,
    isReplayFallback: data.is_replay_fallback === true,
    fallbackReason: typeof data.fallback_reason === 'string' ? data.fallback_reason : undefined,
    timestamp: data.timestamp ?? new Date().toISOString(),
  };
  return NextResponse.json(normalized);
}
