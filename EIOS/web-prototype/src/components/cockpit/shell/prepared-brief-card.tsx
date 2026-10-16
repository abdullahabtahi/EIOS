'use client';

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';
import type { PreparedBrief } from '../state/cockpit-types';
import { MetricProvenanceBadge } from '../common/metric-provenance';
import { SimpleMarkdown } from '../common/simple-markdown';
import { SourceChips } from './source-chips';

type BriefState =
  | { id: string; status: 'ready'; brief: PreparedBrief }
  | { id: string; status: 'none' }
  | { id: string; status: 'error'; httpStatus: number };

/** The brief prepared for this alert; null while no alert is picked. Fetched once per alert, never built here. */
export function usePreparedBrief(entityId: string | null): BriefState | { status: 'loading' } | null {
  const [state, setState] = React.useState<BriefState | null>(null);

  React.useEffect(() => {
    if (!entityId) return;
    let live = true;
    authFetch(`/api/cockpit/ambient/briefs/${encodeURIComponent(entityId)}`, { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        if (!live) return;
        if (res.status === 404) return setState({ id: entityId, status: 'none' });
        if (!res.ok) return setState({ id: entityId, status: 'error', httpStatus: res.status });
        const brief = (await res.json()) as Partial<PreparedBrief> | null;
        // A reply that is not a brief (no text, no readable time) is an error, never an empty card.
        if (!brief || typeof brief.text !== 'string' || !brief.text || Number.isNaN(Date.parse(brief.preparedAt ?? ''))) {
          return setState({ id: entityId, status: 'error', httpStatus: 502 });
        }
        setState({ id: entityId, status: 'ready', brief: brief as PreparedBrief });
      })
      .catch(() => live && setState({ id: entityId, status: 'error', httpStatus: 0 }));
    return () => {
      live = false;
    };
  }, [entityId]);

  if (!entityId) return null;
  return state && state.id === entityId ? state : { status: 'loading' };
}

const clock = (iso: string): string => `${new Date(iso).toISOString().slice(11, 16)} UTC`;

/**
 * "Prepared at 14:05 UTC": the assistant's own brief, run ahead of time under a read-only identity, so it carries the
 * same figures and sources an answer would. With none prepared the card says so; it never shows a placeholder as a brief.
 */
export function PreparedBriefCard({ entityId }: { readonly entityId: string }) {
  const state = usePreparedBrief(entityId);
  if (!state || state.status === 'loading') {
    return <div role="status" aria-label="Loading prepared brief" className="h-16 animate-pulse bg-cx-sub-2 motion-reduce:animate-none" />;
  }
  return (
    <section aria-label="Prepared brief" className="space-y-2.5 border border-slate-200 bg-slate-50/50 p-3.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-title font-sans font-semibold text-slate-900">Prepared brief</h3>
        {state.status === 'ready' && (
          <span className="font-mono text-label text-cx-muted" title={`Valid until ${clock(state.brief.expiresAt)}`}>
            prepared at {clock(state.brief.preparedAt)}
            {state.brief.stale ? ' · older than its time to live' : ''}
          </span>
        )}
      </div>
      {state.status === 'ready' ? (
        <>
          <SimpleMarkdown source={state.brief.text} className="text-xs leading-relaxed text-slate-800 font-sans" />
          {state.brief.citedMetrics.length > 0 && (
            <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-2">
              {state.brief.citedMetrics.map((m) => (
                <MetricProvenanceBadge key={m.metricId} metric={m} displayMode="badge" />
              ))}
            </div>
          )}
          <SourceChips sources={state.brief.sources} />
        </>
      ) : state.status === 'none' ? (
        <p className="text-xs text-cx-muted">
          No brief was prepared for this alert. It is not one of the top alerts, or the preparation has not run yet. Ask the
          assistant to brief you on it.
        </p>
      ) : (
        <p role="alert" className="text-xs text-cx-warn">
          The prepared brief could not be loaded{state.httpStatus ? ` (HTTP ${state.httpStatus})` : ''}. Nothing is shown in its place.
        </p>
      )}
    </section>
  );
}
