'use client';

/**
 * "Verify figures": derive every figure of an answer again through the governed tools and compare. A figure that
 * cannot be derived again is reported as not verified, never as a match; an outage says the check could not run.
 */

import * as React from 'react';
import type { MetricProvenance } from '../state/cockpit-types';
import { authFetch } from '@/lib/auth/token';

interface Row {
  readonly fact_id: string;
  readonly match: boolean;
  readonly error: string | null;
}

type Check =
  | { readonly phase: 'idle' }
  | { readonly phase: 'checking' }
  | { readonly phase: 'done'; readonly checked: number; readonly matched: number; readonly rows: readonly Row[] }
  | { readonly phase: 'failed'; readonly status: number };

function isReply(body: unknown): body is { checked: number; matched: number; rows: Row[] } {
  if (typeof body !== 'object' || body === null) return false;
  const b = body as Record<string, unknown>;
  return (
    typeof b.checked === 'number' &&
    typeof b.matched === 'number' &&
    b.checked > 0 &&
    Array.isArray(b.rows) &&
    b.rows.length === b.checked
  );
}

function shownFigures(figures: readonly MetricProvenance[]) {
  return figures.flatMap((f) => (typeof f.rawValue === 'number' ? [{ fact_id: f.metricId, value: f.rawValue }] : []));
}

export function GeoVerify({ figures, role }: { readonly figures: readonly MetricProvenance[]; readonly role: string }) {
  const [check, setCheck] = React.useState<Check>({ phase: 'idle' });
  const shown = shownFigures(figures);
  if (shown.length === 0) return null;

  const run = async () => {
    setCheck({ phase: 'checking' });
    try {
      const res = await authFetch('/api/cockpit/copilot/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, figures: shown }),
      });
      if (!res.ok) return setCheck({ phase: 'failed', status: res.status });
      const body: unknown = await res.json();
      // A reply without its counts is a failed check, never "all match".
      if (!isReply(body)) return setCheck({ phase: 'failed', status: res.status });
      setCheck({ phase: 'done', checked: body.checked, matched: body.matched, rows: body.rows });
    } catch {
      setCheck({ phase: 'failed', status: 0 });
    }
  };

  if (check.phase === 'done') {
    const all = check.matched === check.checked;
    return (
      <p role="status" className={`text-label ${all ? 'text-cx-ok' : 'text-cx-bad'}`} data-testid="geo-verify-result">
        {all
          ? `Derived again: all ${check.checked} figures match the governed tools.`
          : `Derived again: ${check.matched} of ${check.checked} match. Not verified: ${check.rows
              .filter((r) => !r.match)
              .map((r) => r.fact_id.split(':').pop())
              .join(', ')}.`}
      </p>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={run}
        disabled={check.phase === 'checking'}
        className="flex cursor-pointer items-center gap-1 text-label text-cx-accent hover:underline disabled:opacity-60"
      >
        <span className="material-symbols-sharp text-sm" aria-hidden="true">
          fact_check
        </span>
        {check.phase === 'checking' ? 'Verifying…' : 'Verify figures'}
      </button>
      {check.phase === 'failed' && (
        <span role="alert" className="text-label text-cx-bad">
          The check could not run (HTTP {check.status || 'unreachable'}). Nothing was verified.
        </span>
      )}
    </div>
  );
}
