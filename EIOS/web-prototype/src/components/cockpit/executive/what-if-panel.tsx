'use client';

/**
 * The what-if: move a driver and read what the fitted model says, from the backend, on every change.
 * The effect, its interval, who bears it and what could defend it are all the engine's output; the latency shown
 * is the engine's own (RL-6: under 200 ms, attribution closing to 100.0%).
 */

import * as React from 'react';
import { signed, simulateShock, usd, type Shock, type Simulation } from './board';

const RANGE = 50; // percent of today's level, either way
const DEBOUNCE_MS = 120;
const RL6_MS = 200;

function Tile({ label, value, note, tone }: { label: string; value: string; note: string; tone?: 'ok' | 'bad' | 'warn' }) {
  const color =
    tone === 'ok'
      ? 'text-green-800'
      : tone === 'bad'
      ? 'text-red-700'
      : tone === 'warn'
      ? 'text-amber-800'
      : 'text-slate-900';
  const borderBg =
    tone === 'ok'
      ? 'bg-green-50/50 border-green-200'
      : tone === 'bad'
      ? 'bg-red-50/50 border-red-200'
      : tone === 'warn'
      ? 'bg-amber-50/50 border-amber-200'
      : 'bg-slate-50 border-slate-200';

  return (
    <div className={`p-3 border shadow-2xs space-y-1 ${borderBg}`}>
      <div className="text-[10px] font-mono uppercase text-slate-500 font-semibold tracking-wider truncate">{label}</div>
      <div className={`text-base sm:text-lg font-bold font-mono tabular-nums tracking-tight ${color}`}>{value}</div>
      <div className="text-[11px] font-mono text-slate-500 truncate">{note}</div>
    </div>
  );
}

export function WhatIfPanel({ shock }: { shock: Shock }) {
  const [magnitude, setMagnitude] = React.useState(10);
  const [result, setResult] = React.useState<Simulation | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [roundTripMs, setRoundTripMs] = React.useState<number | null>(null);
  const latest = React.useRef(0);

  React.useEffect(() => {
    const ticket = ++latest.current;
    const timer = setTimeout(async () => {
      const started = performance.now();
      const outcome = await simulateShock(shock.id, magnitude);
      if (ticket !== latest.current) return; // a newer move superseded this one
      setRoundTripMs(Math.round(performance.now() - started));
      if (outcome.ok) {
        setResult(outcome.result);
        setError(null);
      } else {
        setResult(null);
        setError(outcome.reason);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [shock.id, magnitude]);

  const verified = result?.causalLabel === 'VERIFIED_CAUSAL';

  return (
    <section
      aria-label="What-If Parametric Waterfall"
      className="bg-white border border-slate-200 shadow-xs p-4 space-y-4 text-slate-900 select-none h-full flex flex-col justify-between"
    >
      <div className="space-y-4">
        {/* Header with Engine RL-6 Latency Badge */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base text-blue-700">tune</span>
            <h3 className="text-title font-sans font-semibold text-slate-900">
              What if: {shock.label.toLowerCase()}
            </h3>
          </div>
          {result && (
            <span
              className={`px-2 py-0.5 border font-mono text-label font-semibold ${
                result.serverMs < RL6_MS
                  ? 'bg-green-50 text-green-800 border-green-200'
                  : 'bg-red-50 text-red-800 border-red-200'
              }`}
            >
              Engine: <span className="tabular-nums font-bold">{result.serverMs.toFixed(1)} ms</span> (budget {RL6_MS} ms)
              {roundTripMs !== null && <span className="text-slate-500 font-normal"> · round trip {roundTripMs} ms</span>}
            </span>
          )}
        </div>

        {/* Foundry Precision Parameter Slider */}
        <div className="p-3 bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <label htmlFor="exec-shock" className="font-bold text-slate-800">
              {shock.driver}
            </label>
            <span className="font-bold font-mono text-blue-800 bg-blue-50 border border-blue-300 px-2 py-0.5 min-w-16 text-center tabular-nums shadow-2xs">
              {signed(magnitude, 0)}%
            </span>
          </div>
          <input
            id="exec-shock"
            aria-label="What-if shock slider"
            type="range"
            min={-RANGE}
            max={RANGE}
            step={1}
            value={magnitude}
            onChange={(e) => setMagnitude(Number(e.target.value))}
            className="w-full accent-blue-700 cursor-pointer h-2 bg-slate-200 rounded-xs"
          />
          <div className="flex justify-between text-[10px] font-mono text-slate-500">
            <span>-{RANGE}%</span>
            <span>-25%</span>
            <span className="font-bold text-slate-700">0%</span>
            <span>+25%</span>
            <span>+{RANGE}%</span>
          </div>
        </div>

        {error && (
          <p role="alert" className="p-3 text-xs bg-red-50 text-red-800 border border-red-200 font-mono">
            {error}
          </p>
        )}

        {result && (
          <div className="space-y-4">
            {/* 4 Outcome Telemetry Tiles (2x2 Grid) */}
            <div className="grid grid-cols-2 gap-2.5">
              <Tile
                label="Net revenue effect"
                value={usd(result.revenueImpactUsd)}
                note={`${usd(result.intervalLowUsd)} to ${usd(result.intervalHighUsd)}`}
                tone={result.revenueImpactUsd < 0 ? 'bad' : result.revenueImpactUsd > 0 ? 'ok' : undefined}
              />
              <Tile label="Partner churn" value={`${signed(result.churnDeltaPct, 2)} pts`} note="change in churn rate" />
              <Tile label="First-time deposits" value={`${signed(result.firstDepositDeltaPct, 1)}%`} note="28-day count" />
              <Tile
                label="Causal verdict (RL-3)"
                value={verified ? 'Verified' : result.causalLabel ? 'Correlation only' : 'Not assessed'}
                note={result.causalReason ?? ''}
                tone={verified ? 'ok' : result.causalLabel ? 'warn' : undefined}
              />
            </div>

            {result.extrapolates && (
              <p role="status" className="p-2.5 text-label font-mono bg-amber-50 text-amber-800 border border-amber-300">
                This shock takes the driver outside anything in the two-year history, so the fitted effects are not tested there.
              </p>
            )}

            {/* Regional Channel Attribution Distribution */}
            <div className="space-y-2 border-t border-slate-200 pt-3">
              <div className="flex items-center justify-between text-label font-mono text-slate-500">
                <span className="font-semibold uppercase tracking-wider">Who bears it (exposure-weighted by region)</span>
                <span className="text-green-800 font-bold bg-green-50 border border-green-200 px-1.5 py-0.2">
                  Σ Attribution = {result.attributionSum.toFixed(1)}%
                </span>
              </div>
              <div className="space-y-1.5">
                {result.attribution.map((a) => (
                  <div key={a.driver} className="flex items-center gap-2 text-label font-mono">
                    <span className="w-36 truncate text-slate-700 font-semibold">{a.driver}</span>
                    <span className="flex-1 h-2 bg-slate-100 border border-slate-200 rounded-2xs overflow-hidden">
                      <span className="block h-full bg-blue-700" style={{ width: `${a.pct}%` }} />
                    </span>
                    <span className="w-12 text-right tabular-nums font-bold text-slate-800">{a.pct.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Defense Interventions Ranked by Kept Margin */}
            {result.mitigations.length > 0 && (
              <div className="space-y-2 border-t border-slate-200 pt-3">
                <div className="text-label font-mono uppercase tracking-wider text-slate-500 font-semibold">
                  Defences ranked by the margin they keep
                </div>
                <div className="space-y-1.5">
                  {result.mitigations.map((m) => (
                    <div
                      key={m.playbookId}
                      className="p-2.5 bg-slate-50 border border-slate-200 text-label font-mono flex flex-wrap justify-between items-center gap-2"
                    >
                      <span className="font-bold text-slate-900">{m.title}</span>
                      <span className="text-slate-600 tabular-nums">
                        {m.region} · {m.partners} partners · cost {usd(m.costUsd)} ·{' '}
                        <strong className="text-green-800">keeps {usd(m.marginKeptUsd)}</strong>
                      </span>
                    </div>
                  ))}
                </div>
                {result.mitigationBasis && (
                  <p className="text-label text-slate-500 font-sans">{result.mitigationBasis}.</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
