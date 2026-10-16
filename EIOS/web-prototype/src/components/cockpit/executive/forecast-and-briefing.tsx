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
      className="bg-white border border-slate-200 p-4 shadow-xs space-y-3.5 select-none text-slate-900"
    >
      {/* Header Ribbon */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-blue-700">trending_up</span>
          <h3 className="text-title font-sans font-semibold text-slate-900">
            Net revenue, {forecast.horizonDays ?? 28} days ahead
          </h3>
        </div>
        <div className="flex items-center gap-2 text-label font-mono">
          <span className="px-2 py-0.5 bg-slate-100 border border-slate-300 text-slate-700 font-bold">
            HORIZON: {forecast.horizonDays ?? 28}D
          </span>
          <span className="px-2 py-0.5 bg-blue-50 border border-blue-200 text-blue-800 font-bold">
            GAUSSIAN DRIFT ESTIMATE
          </span>
        </div>
      </div>

      {/* Primary KPI & Visual Confidence Envelope */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
        {/* Left: Point Estimate */}
        <div className="lg:col-span-5 space-y-1">
          <div className="text-label font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Point Estimate Projected Revenue
          </div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 font-mono">
            <span className="text-3xl font-extrabold text-slate-900 tabular-nums tracking-tight">
              {usd(forecast.point)}
            </span>
            <span
              className={`text-xs font-bold px-2 py-0.5 border tabular-nums ${
                forecast.deltaPct < 0
                  ? 'bg-amber-50 border-amber-300 text-amber-800'
                  : 'bg-green-50 border-green-300 text-green-800'
              }`}
            >
              {signed(forecast.deltaPct)}% against today
            </span>
          </div>
        </div>

        {/* Right: Palantir Range Gauge */}
        <div className="lg:col-span-7 bg-slate-50 border border-slate-200 p-3 space-y-2 font-mono text-label">
          <div className="flex items-center justify-between">
            <span className="font-semibold uppercase tracking-wider text-slate-500">Credible Interval Distribution</span>
            <span className="text-slate-800 font-bold">{interval}</span>
          </div>

          {forecast.low !== null && forecast.high !== null && (
            <div className="space-y-1 pt-0.5">
              <div className="relative h-3 bg-slate-200 border border-slate-300 rounded-xs overflow-hidden">
                <div className="absolute inset-y-0 left-0 right-0 bg-blue-100/90" />
                <div
                  className="absolute top-0 bottom-0 w-1.5 bg-slate-900 z-10 -translate-x-1/2"
                  style={{ left: `${envelopePct}%` }}
                  title={`Point: ${usd(forecast.point)}`}
                />
              </div>
              <div className="flex items-center justify-between text-slate-500 text-[10px]">
                <span>Low: <strong>{usd(forecast.low)}</strong></span>
                <span className="font-bold text-slate-900">▲ Point: {usd(forecast.point)}</span>
                <span>High: <strong>{usd(forecast.high)}</strong></span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Structured Telemetry Calibration Strip (No duplicate paragraphs) */}
      {forecast.skill !== null && forecast.coverage !== null && forecast.origins !== null && (
        <div className="pt-2 border-t border-slate-200 flex flex-wrap items-center gap-2 text-label font-mono">
          <span className="px-2 py-1 bg-slate-100 border border-slate-300 text-slate-700">
            Backtested on {forecast.origins} past forecasts: its error was <strong className="text-slate-900 font-bold">{forecast.skill.toFixed(2)}× the error of carrying</strong> today&apos;s value forward
          </span>
          <span className="px-2 py-1 bg-green-50 border border-green-200 text-green-800">
            Calibration: <strong className="text-green-900 font-bold">interval held {(forecast.coverage * 100).toFixed(0)}%</strong> of the time on holdouts
          </span>
          {forecast.assumption && (
            <span className="px-2 py-1 bg-slate-100 border border-slate-300 text-slate-700">
              Assumes the {forecast.assumption}.
            </span>
          )}
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
