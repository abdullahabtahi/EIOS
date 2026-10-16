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
    <section
      aria-label="Strategic Trade-off Analysis"
      className="bg-white border border-slate-200 p-4 shadow-xs space-y-4 text-slate-900 select-none h-full flex flex-col justify-between"
    >
      <div className="space-y-4">
        {/* Header Ribbon */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base text-slate-700">balance</span>
            <h3 className="text-title font-sans font-semibold text-slate-900">Strategic Trade-off Analysis</h3>
          </div>
          <span className="text-label font-mono text-slate-500 uppercase tracking-wider font-semibold">
            Two-Phase Governed Plays
          </span>
        </div>

        {/* Section 1: Portfolio Exposure Risks */}
        <div className="space-y-2">
          <div className="text-label font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Largest risks by expected exposure
          </div>
          <div className="space-y-1.5">
            {risks.map((r) => (
              <div
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-2 p-2.5 bg-slate-50 border border-slate-200 text-xs hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center gap-2 font-semibold text-slate-800">
                  <span className="material-symbols-sharp text-xs text-amber-600">warning</span>
                  <span>{r.title}</span>
                </div>
                <div className="font-mono text-label tabular-nums flex items-center gap-1.5">
                  <span
                    className={`px-1.5 py-0.2 font-bold border text-[10px] ${
                      r.severity === 'HIGH'
                        ? 'bg-red-50 text-red-800 border-red-300'
                        : 'bg-amber-50 text-amber-800 border-amber-300'
                    }`}
                  >
                    {r.severity}
                  </span>
                  <span className="text-slate-500">· exposure</span>
                  <strong className="text-slate-900 font-bold">{usd(r.exposureUsd)}</strong>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section 2: Margin-Accretive Retention Plays */}
        <div className="space-y-2 border-t border-slate-200 pt-3">
          <div className="text-label font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Retention plays the hazard model prices as worth doing
          </div>
          {opportunities.length === 0 && (
            <p className="text-xs text-slate-500 font-mono p-3 bg-slate-50 border border-slate-200">
              No play currently keeps more margin than it costs.
            </p>
          )}
          <div className="space-y-2.5">
            {opportunities.map((o) => {
              const phase: Phase = phases[o.id] ?? { phase: 'idle' };
              return (
                <div key={o.id} className="p-3 bg-slate-50 border border-slate-200 space-y-2.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold text-slate-900">{o.title}</span>
                    <span className="text-label font-mono text-green-800 bg-green-50 border border-green-200 px-2 py-0.5 font-bold tabular-nums">
                      keeps {usd(o.upsideUsd)}
                    </span>
                  </div>
                  <p className="text-label font-mono text-slate-500 leading-normal">
                    <span className="px-1.5 py-0.2 bg-white border border-slate-300 text-slate-700 font-semibold mr-1.5">
                      {o.actionType}
                    </span>
                    model projection under the hazard model, not a causal estimate
                  </p>
                  {o.stage ? (
                    <button
                      type="button"
                      disabled={phase.phase === 'staging' || phase.phase === 'staged'}
                      onClick={() => stage(o)}
                      className="w-full py-2 bg-slate-900 hover:bg-black disabled:opacity-50 text-white text-xs font-mono font-bold cursor-pointer flex items-center justify-center gap-1.5 transition-colors border border-slate-900 shadow-2xs"
                    >
                      <span className="material-symbols-sharp text-sm">playlist_add</span>
                      <span>
                        {phase.phase === 'staging'
                          ? 'Staging…'
                          : phase.phase === 'staged'
                          ? `Staged (${phase.state})`
                          : 'Stage through the intent hub'}
                      </span>
                    </button>
                  ) : (
                    <p className="text-label text-slate-500 font-mono">This play cannot be staged from here.</p>
                  )}
                  {phase.phase === 'error' && (
                    <p role="alert" className="text-label text-red-700 font-mono bg-red-50 border border-red-200 p-2">
                      {phase.message}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
