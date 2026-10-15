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
  const color = tone === 'ok' ? 'text-cx-ok' : tone === 'bad' ? 'text-cx-bad' : tone === 'warn' ? 'text-cx-warn' : 'text-cx-ink';
  return (
    <div className="p-2.5 bg-cx-sub border border-cx-line">
      <div className="text-label font-mono uppercase text-cx-muted tracking-wider">{label}</div>
      <div className={`text-base font-bold font-mono mt-0.5 tabular-nums ${color}`}>{value}</div>
      <div className="text-label font-mono text-cx-muted mt-0.5">{note}</div>
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
    <section aria-label="What-If Parametric Waterfall" className="bg-white border border-cx-line shadow-xs p-4 space-y-4 text-cx-ink">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cx-line-soft pb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-cx-accent">tune</span>
          <h3 className="text-title font-sans font-semibold">What if: {shock.label.toLowerCase()}</h3>
        </div>
        {result && (
          <span
            className={`px-2 py-0.5 border font-mono text-label font-semibold ${
              result.serverMs < RL6_MS ? 'bg-cx-ok-bg text-cx-ok border-cx-ok-line' : 'bg-cx-bad-bg text-cx-bad border-cx-bad-line'
            }`}
          >
            Engine: <span className="tabular-nums">{result.serverMs.toFixed(1)} ms</span> (budget {RL6_MS} ms)
            {roundTripMs !== null && <span className="text-cx-muted font-normal"> · round trip {roundTripMs} ms</span>}
          </span>
        )}
      </div>

      <div className="p-3 bg-cx-sub border border-cx-line space-y-2">
        <div className="flex items-center justify-between text-xs font-mono">
          <label htmlFor="exec-shock" className="font-semibold">
            {shock.driver}
          </label>
          <span className="font-bold text-cx-accent bg-cx-info-bg border border-cx-info-line px-2 py-0.5 min-w-16 text-center tabular-nums">
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
          className="w-full accent-cx-accent cursor-pointer"
        />
        <div className="flex justify-between text-label font-mono text-cx-muted">
          <span>-{RANGE}%</span>
          <span>0%</span>
          <span>+{RANGE}%</span>
        </div>
      </div>

      {error && (
        <p role="alert" className="p-3 text-xs bg-cx-bad-bg text-cx-bad border border-cx-bad-line">
          {error}
        </p>
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
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
            <p role="status" className="p-2.5 text-label bg-cx-warn-bg text-cx-warn border border-cx-warn-line">
              This shock takes the driver outside anything in the two-year history, so the fitted effects are not tested there.
            </p>
          )}

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-label font-mono text-cx-muted">
              <span>Who bears it (exposure-weighted by region)</span>
              <span className="text-cx-ok font-semibold">Σ Attribution = {result.attributionSum.toFixed(1)}%</span>
            </div>
            {result.attribution.map((a) => (
              <div key={a.driver} className="flex items-center gap-2 text-label font-mono">
                <span className="w-36 truncate">{a.driver}</span>
                <span className="flex-1 h-2 bg-cx-sub border border-cx-line">
                  <span className="block h-full bg-cx-accent" style={{ width: `${a.pct}%` }} />
                </span>
                <span className="w-12 text-right tabular-nums">{a.pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>

          {result.mitigations.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-label font-mono text-cx-muted">Defences ranked by the margin they keep</div>
              {result.mitigations.map((m) => (
                <div key={m.playbookId} className="p-2 bg-cx-sub border border-cx-line text-label font-mono flex flex-wrap justify-between gap-2">
                  <span className="font-semibold text-cx-ink">{m.title}</span>
                  <span className="text-cx-muted tabular-nums">
                    {m.region} · {m.partners} partners · cost {usd(m.costUsd)} · keeps {usd(m.marginKeptUsd)}
                  </span>
                </div>
              ))}
              {result.mitigationBasis && <p className="text-label text-cx-muted font-sans">{result.mitigationBasis}.</p>}
            </div>
          )}
        </>
      )}
    </section>
  );
}
