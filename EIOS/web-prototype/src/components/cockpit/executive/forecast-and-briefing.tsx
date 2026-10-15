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
  return (
    <section aria-label="Net revenue projection" className="bg-white border border-cx-line p-4 space-y-2 shadow-xs">
      <div className="flex items-center gap-2 border-b border-cx-line-soft pb-2">
        <span className="material-symbols-sharp text-base text-cx-accent">trending_up</span>
        <h3 className="text-title font-sans font-semibold text-cx-ink">
          Net revenue, {forecast.horizonDays ?? 28} days ahead
        </h3>
      </div>
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 font-mono">
        <span className="text-xl font-bold text-cx-ink tabular-nums">{usd(forecast.point)}</span>
        <span className="text-xs text-cx-muted tabular-nums">{signed(forecast.deltaPct)}% against today</span>
      </div>
      <p className="text-label font-mono text-cx-ink-soft">{interval}</p>
      {forecast.skill !== null && forecast.coverage !== null && forecast.origins !== null && (
        <p className="text-label font-sans text-cx-muted leading-relaxed">
          Backtested on {forecast.origins} past forecasts: its error was {forecast.skill.toFixed(2)}× the error of carrying
          today&apos;s value forward, and the interval held {(forecast.coverage * 100).toFixed(0)}% of the time on forecasts held
          out from its calibration.
          {forecast.assumption && <> Assumes the {forecast.assumption}.</>}
        </p>
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
      <div className="flex items-center gap-2 border-b border-cx-line pb-2">
        <span className="material-symbols-sharp text-base text-cx-accent">wb_twilight</span>
        <h3 className="text-title font-sans font-semibold text-cx-ink">Executive Morning Briefing</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        {horizons.map((h) => (
          <div key={h.name} className="p-3.5 bg-white border border-cx-line shadow-xs flex flex-col justify-between space-y-2">
            <div>
              <span className="text-label font-mono font-bold text-cx-accent bg-cx-info-bg border border-cx-info-line px-1">
                {BADGE[h.name] ?? h.name.toUpperCase()}
              </span>
              <p className="text-label text-cx-ink-soft font-sans mt-2 leading-relaxed">{h.headline}</p>
            </div>
            <div className="pt-2 border-t border-cx-line-soft flex items-center justify-between">
              <MetricProvenanceBadge metric={toMetric(h)} displayMode="compact" />
              <span className="text-label font-mono text-cx-muted tabular-nums">{signed(h.deltaPct)}%</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
