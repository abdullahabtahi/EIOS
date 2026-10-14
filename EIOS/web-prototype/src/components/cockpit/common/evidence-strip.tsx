'use client';

/**
 * The AML evidence strip for the selected case: computed tiles and the figures behind them, each with its
 * provenance popover. Everything shown arrives from the backend for this account; a missing part is omitted.
 */
import * as React from 'react';
import type { EvidenceStrip } from '../state/cockpit-types';
import { MetricProvenanceBadge } from './metric-provenance';

const SEVERITY_STYLE: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 border-red-200',
  HIGH: 'bg-amber-100 text-amber-800 border-amber-200',
  MEDIUM: 'bg-amber-100 text-amber-800 border-amber-200',
};

export function EvidenceStripPanel({ strip }: { strip: EvidenceStrip }) {
  const severityStyle = SEVERITY_STYLE[strip.severity] ?? 'bg-slate-100 text-slate-700 border-slate-200';
  return (
    <section aria-label="AML Evidence KPI Strip" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-red-600">shield_with_heart</span>
          <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">{strip.title}</h3>
        </div>
        <span className={`text-label font-mono px-1.5 py-0.5 border font-bold ${severityStyle}`}>
          {strip.score === null ? 'NO ALERT' : `SEVERITY: ${strip.severity} (SCORE: ${strip.score.toFixed(2)})`}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
        {strip.tiles.map((tile) => (
          <div key={tile.label} className="p-3 bg-slate-50 border border-slate-200" data-testid="evidence-tile">
            <span className="text-label text-slate-500 block">{tile.label}</span>
            <div className={`text-base font-bold mt-0.5 ${tile.tone === 'alert' ? 'text-red-700' : 'text-slate-900'}`}>
              {tile.value}
            </div>
            <span className="text-label text-slate-500 block mt-0.5">{tile.caption}</span>
          </div>
        ))}
      </div>

      {strip.metrics.length > 0 && (
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
          {strip.metrics.map((metric) => (
            <MetricProvenanceBadge key={metric.metricId} metric={metric} displayMode="badge" />
          ))}
        </div>
      )}
    </section>
  );
}
