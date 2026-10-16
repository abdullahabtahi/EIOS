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

  return (
    <section
      aria-label="Net revenue projection"
      className="bg-white border border-slate-200 shadow-xs select-none text-slate-900 overflow-hidden"
    >
      {/* Header Ribbon */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-slate-200/90 bg-slate-50/50">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-blue-700">trending_up</span>
          <h3 className="text-title font-sans font-semibold text-slate-900 tracking-tight">
            Net revenue, {forecast.horizonDays ?? 28} days ahead
          </h3>
        </div>
        <div className="flex items-center gap-1.5 text-label font-mono">
          <span className="px-2 py-0.5 bg-white border border-slate-200 text-slate-600 font-semibold tracking-wider text-[10px]">
            HORIZON: {forecast.horizonDays ?? 28}D
          </span>
          <span className="px-2 py-0.5 bg-blue-50 border border-blue-200 text-blue-800 font-semibold tracking-wider text-[10px]">
            GAUSSIAN DRIFT ESTIMATE
          </span>
        </div>
      </div>

      {/* Primary KPI & Visual Confidence Envelope */}
      <div className="p-4 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Left: Point Estimate */}
        <div className="lg:col-span-5 space-y-1.5">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Point Estimate Projected Revenue
          </div>
          <div className="flex flex-wrap items-baseline gap-3 font-mono">
            <span className="text-3xl font-extrabold text-slate-900 tabular-nums tracking-tight">
              {usd(forecast.point)}
            </span>
            <span
              className={`text-[11px] font-bold px-2 py-0.5 border tabular-nums ${
                forecast.deltaPct < 0
                  ? 'bg-amber-50 border-amber-300 text-amber-800'
                  : 'bg-green-50 border-green-300 text-green-800'
              }`}
            >
              {signed(forecast.deltaPct)}% against today
            </span>
          </div>
        </div>

        {/* Right: Palantir Statistical Range Gauge */}
        <div className="lg:col-span-7 space-y-2">
          <div className="flex items-center justify-between text-label font-mono">
            <span className="font-semibold uppercase tracking-wider text-slate-500 text-[10px]">
              Credible Interval Distribution
            </span>
            <span className="text-slate-800 font-bold">{interval}</span>
          </div>

          {forecast.low !== null && forecast.high !== null && (
            <div className="space-y-1.5 pt-0.5">
              {/* Statistical Distribution Axis Track */}
              <div className="relative h-3.5 bg-slate-100 border border-slate-300/80 rounded-xs overflow-hidden flex items-center">
                {/* 90% Confidence Mass Fill */}
                <div className="absolute inset-y-0 left-0 right-0 bg-blue-100/70 border-x border-blue-300" />
                {/* Center Reference Guide */}
                <div className="absolute top-0 bottom-0 left-1/2 w-px bg-blue-200" />
                {/* Mode Point Estimate Needle */}
                <div
                  className="absolute top-0 bottom-0 w-1 bg-slate-900 z-10 -translate-x-1/2 shadow-xs"
                  style={{ left: `${envelopePct}%` }}
                  title={`Point: ${usd(forecast.point)}`}
                />
              </div>
              {/* Coordinate Callouts */}
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span>Low: <strong className="text-slate-700">{usd(forecast.low)}</strong></span>
                <span className="font-bold text-slate-900 bg-slate-100 px-1.5 py-0.2 border border-slate-200">
                  ▲ Point: {usd(forecast.point)}
                </span>
                <span>High: <strong className="text-slate-700">{usd(forecast.high)}</strong></span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Model Telemetry & Audit Footer Strip */}
      {forecast.skill !== null && forecast.coverage !== null && forecast.origins !== null && (
        <div className="border-t border-slate-200/90 bg-slate-50/70 px-4 py-2.5 text-label font-mono">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 divide-y md:divide-y-0 md:divide-x divide-slate-200 text-slate-600">
            {/* Benchmark */}
            <div className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-1 shrink-0" />
              <span className="leading-snug text-[11px]">
                Backtested on {forecast.origins} past forecasts: its error was{' '}
                <strong className="text-slate-900 font-semibold">
                  {forecast.skill.toFixed(2)}× the error of carrying
                </strong>{' '}
                today&apos;s value forward
              </span>
            </div>

            {/* Calibration */}
            <div className="flex items-start gap-2 md:pl-3 pt-2 md:pt-0">
              <span className="w-1.5 h-1.5 rounded-full bg-green-600 mt-1 shrink-0" />
              <span className="leading-snug text-[11px]">
                Calibration:{' '}
                <strong className="text-slate-900 font-semibold">
                  interval held {(forecast.coverage * 100).toFixed(0)}%
                </strong>{' '}
                of the time on holdouts
              </span>
            </div>

            {/* Prior Assumption */}
            {forecast.assumption && (
              <div className="flex items-start gap-2 md:pl-3 pt-2 md:pt-0">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1 shrink-0" />
                <span className="leading-snug text-[11px] text-slate-500">
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
