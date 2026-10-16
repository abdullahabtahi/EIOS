'use client';

/**
 * The sealed evidence of a decision turn (a hold proposed, a SAR drafted): its SHA-256, which staging signs with the
 * intent, and a replay that asks every recorded call again and compares figure by figure. A failed replay, an altered
 * bundle or an outage never reads as "equal".
 */

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';

interface Replay {
  readonly intact: boolean;
  readonly equal: boolean;
  readonly figures: number;
  readonly differing: number;
  readonly calls: number;
}

type State =
  | { readonly phase: 'idle' }
  | { readonly phase: 'replaying' }
  | { readonly phase: 'done'; readonly replay: Replay }
  | { readonly phase: 'failed'; readonly status: number };

function replayOf(body: unknown): Replay | undefined {
  if (typeof body !== 'object' || body === null) return undefined;
  const b = body as Record<string, unknown>;
  if (typeof b.intact !== 'boolean' || typeof b.equal !== 'boolean' || !Array.isArray(b.calls)) return undefined;
  if (!b.intact) return { intact: false, equal: false, figures: 0, differing: 0, calls: 0 };
  if (typeof b.figures !== 'number' || typeof b.differing !== 'number') return undefined;
  return { intact: true, equal: b.equal, figures: b.figures, differing: b.differing, calls: b.calls.length };
}

function verdict(r: Replay): string {
  if (!r.intact) return 'The bundle no longer matches its hash. It cannot be relied on.';
  if (r.equal) return `Replayed: all ${r.figures} figures from ${r.calls} sealed calls come back the same.`;
  return `Replayed: ${r.differing} of ${r.figures} figures differ from what was sealed. The bundle still holds what the decision saw.`;
}

export function GeoEvidence({ bundleId }: { readonly bundleId: string }) {
  const [state, setState] = React.useState<State>({ phase: 'idle' });

  const run = async () => {
    setState({ phase: 'replaying' });
    try {
      const res = await authFetch(`/api/cockpit/evidence/${bundleId}/replay`, { method: 'POST' });
      if (!res.ok) return setState({ phase: 'failed', status: res.status });
      const replay = replayOf(await res.json());
      setState(replay ? { phase: 'done', replay } : { phase: 'failed', status: res.status });
    } catch {
      setState({ phase: 'failed', status: 0 });
    }
  };

  return (
    <div className="flex flex-col gap-1" data-testid="geo-evidence">
      <div className="flex flex-wrap items-center gap-2 text-label">
        <span className="material-symbols-sharp text-sm text-cx-muted" aria-hidden="true">
          verified
        </span>
        <span className="text-cx-muted">
          Evidence sealed <span title={bundleId}>sha256 {bundleId.slice(0, 12)}…</span>, signed with
          any hold staged from it.
        </span>
        {state.phase !== 'done' && (
          <button
            type="button"
            onClick={run}
            disabled={state.phase === 'replaying'}
            className="cursor-pointer text-cx-accent hover:underline disabled:opacity-60"
          >
            {state.phase === 'replaying' ? 'Replaying…' : 'Replay evidence'}
          </button>
        )}
      </div>
      {state.phase === 'done' && (
        <p
          role="status"
          className={`text-label ${state.replay.equal ? 'text-cx-ok' : 'text-cx-bad'}`}
          data-testid="geo-evidence-result"
        >
          {verdict(state.replay)}
        </p>
      )}
      {state.phase === 'failed' && (
        <span role="alert" className="text-label text-cx-bad">
          The replay could not run (HTTP {state.status || 'unreachable'}). Nothing was compared.
        </span>
      )}
    </div>
  );
}
