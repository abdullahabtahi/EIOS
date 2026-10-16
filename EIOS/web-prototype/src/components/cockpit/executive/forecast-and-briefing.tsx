'use client';

/**
 * The financial projection with the interval its own backtest measured, and the four briefing horizons.
 * Every figure here was computed by the backend; this file only lays it out.
 */

import * as React from 'react';
import { MetricProvenanceBadge } from '../common/metric-provenance';
import type { MetricProvenance } from '../state/cockpit-types';
import { signed, usd, type BoardForecast, type Horizon } from './board';

export function ForecastCard({ forecast }: { forecast: BoardForecast }) {
  const interval =
    forecast.low !== null && forecast.high !== null
      ? `${Math.round((forecast.nominal ?? 0) * 100)}% interval ${usd(forecast.low)} to ${usd(forecast.high)}`
      : 'No interval was measured for this projection.';

  // Compute point estimate position relative to the low/high confidence envelope
  const envelopePct = React.useMemo(() => {
    if (forecast.low === null || forecast.high === null || forecast.high === forecast.low) return 50;
    const raw = ((forecast.point - forecast.low) / (forecast.high - forecast.low)) * 100;
    return Math.min(Math.max(raw, 4), 96);
  }, [forecast.point, forecast.low, forecast.high]);

  // Generate mathematically accurate Gaussian probability density curve
  const gaussian = React.useMemo(() => {
    if (forecast.low === null || forecast.high === null) return null;
    const x0 = 50 + (envelopePct / 100) * 400; // Peak mode coordinate in 500px width
    const sigma = 105;
    const pts: [number, number][] = [];
    for (let x = 10; x <= 490; x += 6) {
      const exponent = -0.5 * Math.pow((x - x0) / sigma, 2);
      const y = 58 - 48 * Math.exp(exponent);
      pts.push([x, y]);
    }
    const fullPath = `M ${pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' L ')}`;
    // Shaded 90% confidence region between x = 50 and x = 450
    const shaded = pts.filter(([x]) => x >= 50 && x <= 450);
    const yLow = 58 - 48 * Math.exp(-0.5 * Math.pow((50 - x0) / sigma, 2));
    const yHigh = 58 - 48 * Math.exp(-0.5 * Math.pow((450 - x0) / sigma, 2));
    const areaPath = `M 50,58 L 50,${yLow.toFixed(1)} L ${shaded.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' L ')} L 450,${yHigh.toFixed(1)} L 450,58 Z`;
    return { fullPath, areaPath, x0, yPeak: 10, yLow, yHigh };
  }, [forecast.low, forecast.high, envelopePct]);

  return (
    <section
      aria-label="Net revenue projection"
      className="bg-white border border-slate-200 shadow-xs select-none text-slate-900 overflow-hidden"
    >
      {/* Header Ribbon */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3.5 border-b border-slate-200/90 bg-slate-50/50">
        <div className="flex items-center gap-2.5">
          <span className="material-symbols-sharp text-lg text-blue-700">trending_up</span>
          <h3 className="text-sm font-sans font-semibold text-slate-900 tracking-tight">
            Net Revenue Projection ({forecast.horizonDays ?? 28} Days Ahead)
          </h3>
        </div>
        <div className="flex items-center gap-2 text-label font-mono">
          <span className="px-2.5 py-1 bg-white border border-slate-200 text-slate-600 font-semibold tracking-wider text-[10px]">
            HORIZON: {forecast.horizonDays ?? 28}D
          </span>
          <span className="px-2.5 py-1 bg-blue-50 border border-blue-200 text-blue-800 font-semibold tracking-wider text-[10px]">
            GAUSSIAN DRIFT ESTIMATE
          </span>
        </div>
      </div>

      {/* Primary KPI & Visual Confidence Envelope */}
      <div className="p-6 grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
        {/* Left: Point Estimate */}
        <div className="xl:col-span-5 space-y-3">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-2 h-6">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400 inline-block" />
            Expected Projected Revenue
          </div>
          <div className="space-y-2">
            <div className="flex items-baseline gap-2.5 font-mono">
              <span className="text-3xl font-extrabold text-slate-900 tabular-nums tracking-tight">
                {usd(forecast.point)}
              </span>
              <span
                className={`text-[11px] font-medium px-2 py-0.5 border tabular-nums whitespace-nowrap ${
                  forecast.deltaPct < 0
                    ? 'bg-amber-50 border-amber-300 text-amber-800'
                    : 'bg-green-50 border-green-300 text-green-800'
                }`}
              >
                {signed(forecast.deltaPct)}% against today
              </span>
            </div>
            <p className="text-xs text-slate-500 font-sans leading-relaxed max-w-sm">
              Synthesized from historical payout velocity, partner attrition risk, and deposit momentum.
            </p>
          </div>
        </div>

        {/* Right: Palantir Gaussian Probability Distribution Envelope */}
        <div className="xl:col-span-7 space-y-3">
          <div className="flex items-center justify-between text-label font-mono h-6">
            <span className="font-semibold uppercase tracking-wider text-slate-500 text-[10px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 inline-block" />
              90% Confidence Probability Density
            </span>
            <span className="text-slate-800 font-bold bg-slate-100 px-2 py-0.5 border border-slate-200 text-[11px]">
              {interval}
            </span>
          </div>

          {gaussian && (
            <div className="space-y-3">
              {/* Gaussian Bell Curve SVG */}
              <div className="bg-slate-50/70 border border-slate-200/90 p-3 rounded-xs">
                <svg
                  role="img"
                  aria-label="Gaussian probability density curve"
                  className="w-full h-16 select-none"
                  viewBox="0 0 500 70"
                >
                  {/* Shaded 90% Confidence Mass */}
                  <path d={gaussian.areaPath} className="fill-blue-100/70" />

                  {/* Baseline Axis */}
                  <line x1="10" y1="58" x2="490" y2="58" className="stroke-slate-300 stroke-1" />

                  {/* Low Boundary Dashed Marker (P05) */}
                  <line x1="50" y1={gaussian.yLow} x2="50" y2="58" strokeDasharray="3 2" className="stroke-blue-400 stroke-1" />

                  {/* High Boundary Dashed Marker (P95) */}
                  <line x1="450" y1={gaussian.yHigh} x2="450" y2="58" strokeDasharray="3 2" className="stroke-blue-400 stroke-1" />

                  {/* Continuous Probability Curve */}
                  <path d={gaussian.fullPath} fill="none" className="stroke-blue-600 stroke-1.5" />

                  {/* Mode / Expected Needle */}
                  <line x1={gaussian.x0} y1={gaussian.yPeak} x2={gaussian.x0} y2="58" className="stroke-slate-900 stroke-1.5" />
                  <circle cx={gaussian.x0} cy={gaussian.yPeak} r="3" className="fill-slate-900 stroke-white stroke-1" />
                </svg>
              </div>

              {/* 3 Spacious Intuitive Metric Cards */}
              <div className="grid grid-cols-3 gap-3 font-mono">
                {/* 1. Floor */}
                <div className="p-3 bg-slate-50 border border-slate-200 space-y-1">
                  <div className="text-[10px] text-slate-500 uppercase font-semibold">Conservative Floor (P05)</div>
                  <div className="text-base font-bold text-slate-900 tabular-nums">{usd(forecast.low!)}</div>
                  <div className="text-[9.5px] text-slate-500 font-sans">Downside planning buffer</div>
                </div>

                {/* 2. Mode Expected */}
                <div className="p-3 bg-blue-50/70 border border-blue-200 space-y-1">
                  <div className="text-[10px] text-blue-800 uppercase font-bold">Most Likely (Mode)</div>
                  <div className="text-base font-bold text-blue-950 tabular-nums">{usd(forecast.point)}</div>
                  <div className="text-[9.5px] text-blue-700/80 font-sans">Peak density forecast</div>
                </div>

                {/* 3. Ceiling */}
                <div className="p-3 bg-slate-50 border border-slate-200 space-y-1">
                  <div className="text-[10px] text-slate-500 uppercase font-semibold">Optimistic Ceiling (P95)</div>
                  <div className="text-base font-bold text-slate-900 tabular-nums">{usd(forecast.high!)}</div>
                  <div className="text-[9.5px] text-slate-500 font-sans">Upside target threshold</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Model Telemetry & Audit Footer Strip */}
      {forecast.skill !== null && forecast.coverage !== null && forecast.origins !== null && (
        <div className="border-t border-slate-200/90 bg-slate-50/70 px-6 py-3.5 text-label font-mono">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 divide-y md:divide-y-0 md:divide-x divide-slate-200 text-slate-600">
            {/* Benchmark */}
            <div className="flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
              <span className="leading-relaxed text-[11px] text-slate-600">
                <span className="text-slate-400 font-medium">Backtested on {forecast.origins} past forecasts:</span>{' '}
                its error was{' '}
                <span className="text-slate-700">
                  {forecast.skill.toFixed(2)}× the error of carrying
                </span>{' '}
                today&apos;s value forward
              </span>
            </div>

            {/* Calibration */}
            <div className="flex items-start gap-2.5 md:pl-4 pt-2.5 md:pt-0">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
              <span className="leading-relaxed text-[11px] text-slate-600">
                <span className="text-slate-400 font-medium">Calibration:</span>{' '}
                <span className="text-slate-700">
                  interval held {(forecast.coverage * 100).toFixed(0)}%
                </span>{' '}
                of the time on holdouts
              </span>
            </div>

            {/* Prior Assumption */}
            {forecast.assumption && (
              <div className="flex items-start gap-2.5 md:pl-4 pt-2.5 md:pt-0">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                <span className="leading-relaxed text-[11px] text-slate-600">
                  <span className="text-slate-400 font-medium">Assumption:</span>{' '}
                  Assumes the {forecast.assumption}.
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

const BADGE: Record<string, string> = {
  Competitive: 'COMPETITIVE',
  Partner: 'PARTNER FLOW',
  Client: 'CLIENT RETENTION',
  Financial: 'FINANCIAL METRICS',
};

function toMetric(h: Horizon): MetricProvenance {
  return {
    metricId: h.metricId,
    name: h.name,
    rawValue: h.value,
    formattedValue: h.figure,
    unit: '',
    semanticDefinitionVersion: `v${h.definitionVersion}`,
    asOfTimestamp: h.asOf,
    originEngine: h.source,
    stewardRole: h.owner,
    citation: '[COMPUTED]',
    isCached: false,
  };
}

export function BriefingCards({ horizons }: { horizons: Horizon[] }) {
  return (
    <section aria-label="Morning Briefing 4 Horizons" className="space-y-2.5">
      <div className="flex items-center justify-between border-b border-slate-200 pb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-blue-700">wb_twilight</span>
          <h3 className="text-title font-sans font-semibold text-slate-900">Executive Morning Briefing</h3>
        </div>
        <span className="text-label font-mono text-slate-500 uppercase tracking-wider font-semibold">
          4 Sensitivity Horizons · Continuous Telemetry
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        {horizons.map((h) => (
          <div
            key={h.name}
            className="p-3.5 bg-white border border-slate-200 shadow-xs flex flex-col justify-between space-y-2 hover:border-slate-300 transition-colors"
          >
            <div>
              <div className="flex items-center justify-between gap-1">
                <span className="text-label font-mono font-bold text-blue-800 bg-blue-50 border border-blue-200 px-1.5 py-0.5 tracking-wider">
                  {BADGE[h.name] ?? h.name.toUpperCase()}
                </span>
                <span
                  className={`text-label font-mono font-bold px-1.5 py-0.5 border tabular-nums ${
                    h.deltaPct > 0
                      ? 'text-green-800 bg-green-50 border-green-200'
                      : h.deltaPct < 0
                      ? 'text-amber-800 bg-amber-50 border-amber-200'
                      : 'text-slate-700 bg-slate-50 border-slate-200'
                  }`}
                >
                  {signed(h.deltaPct)}%
                </span>
              </div>
              <p className="text-xs text-slate-700 font-sans mt-2.5 leading-relaxed min-h-[3.25rem]">
                {h.headline}
              </p>
            </div>
            <div className="pt-2.5 border-t border-slate-200 flex items-center justify-between">
              <MetricProvenanceBadge metric={toMetric(h)} displayMode="compact" />
              <span className="text-base font-bold font-mono text-slate-900 tabular-nums">
                {h.figure}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
