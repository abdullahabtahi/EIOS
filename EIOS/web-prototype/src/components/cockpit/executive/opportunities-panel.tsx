'use client';

/**
 * Risks and the opportunities the engines priced. Staging an opportunity goes through the intent hub with the
 * backend-built request; the card that comes back is signed and ledgered there. Nothing is staged by this file.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { GovernedActionError, stageProposal } from '@/lib/actions/governed-actions';
import { usd, type BoardOpportunity, type BoardRisk } from './board';

type Phase = { phase: 'idle' } | { phase: 'staging' } | { phase: 'staged'; state: string } | { phase: 'error'; message: string };

export function OpportunitiesPanel({ risks, opportunities }: { risks: BoardRisk[]; opportunities: BoardOpportunity[] }) {
  const { stageAction } = useCockpit();
  const [phases, setPhases] = React.useState<Record<string, Phase>>({});

  const stage = async (o: BoardOpportunity) => {
    if (!o.stage) return;
    setPhases((p) => ({ ...p, [o.id]: { phase: 'staging' } }));
    try {
      const card = await stageProposal(o.stage);
      stageAction(card);
      setPhases((p) => ({ ...p, [o.id]: { phase: 'staged', state: card.lifecycleState } }));
    } catch (err) {
      const message = err instanceof GovernedActionError ? err.message : 'Staging failed. Nothing was staged.';
      setPhases((p) => ({ ...p, [o.id]: { phase: 'error', message } }));
    }
  };

  return (
    <section aria-label="Strategic Trade-off Analysis" className="bg-white border border-cx-line p-4 shadow-xs space-y-4">
      <div className="flex items-center gap-2 border-b border-cx-line-soft pb-2">
        <span className="material-symbols-sharp text-base text-cx-ink">balance</span>
        <h3 className="text-title font-sans font-semibold text-cx-ink">Strategic Trade-off Analysis</h3>
      </div>

      <div className="space-y-1.5">
        <div className="text-label font-mono text-cx-muted">Largest risks by expected exposure</div>
        {risks.map((r) => (
          <div key={r.id} className="flex flex-wrap items-center justify-between gap-2 p-2 bg-cx-sub border border-cx-line text-xs">
            <span className="text-cx-ink">{r.title}</span>
            <span className="font-mono text-label tabular-nums">
              <span className={r.severity === 'HIGH' ? 'text-cx-bad font-bold' : 'text-cx-warn font-bold'}>{r.severity}</span>
              <span className="text-cx-muted"> · exposure {usd(r.exposureUsd)}</span>
            </span>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <div className="text-label font-mono text-cx-muted">Retention plays the hazard model prices as worth doing</div>
        {opportunities.length === 0 && <p className="text-xs text-cx-muted">No play currently keeps more margin than it costs.</p>}
        {opportunities.map((o) => {
          const phase: Phase = phases[o.id] ?? { phase: 'idle' };
          return (
            <div key={o.id} className="p-3 bg-cx-sub border border-cx-line space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-bold text-cx-ink">{o.title}</span>
                <span className="text-label font-mono text-cx-ok font-bold tabular-nums">keeps {usd(o.upsideUsd)}</span>
              </div>
              <p className="text-label font-mono text-cx-muted">
                {o.actionType} · model projection under the hazard model, not a causal estimate
              </p>
              {o.stage ? (
                <button
                  type="button"
                  disabled={phase.phase === 'staging' || phase.phase === 'staged'}
                  onClick={() => stage(o)}
                  className="w-full py-1.5 bg-cx-ink hover:bg-black disabled:opacity-50 text-white text-xs font-semibold cursor-pointer flex items-center justify-center gap-1"
                >
                  <span className="material-symbols-sharp text-xs">playlist_add</span>
                  {phase.phase === 'staging' ? 'Staging…' : phase.phase === 'staged' ? `Staged (${phase.state})` : 'Stage through the intent hub'}
                </button>
              ) : (
                <p className="text-label text-cx-muted">This play cannot be staged from here.</p>
              )}
              {phase.phase === 'error' && (
                <p role="alert" className="text-label text-cx-bad">
                  {phase.message}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
