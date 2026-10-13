'use client';

/**
 * Metric Provenance Badge & Citation Popover
 * Enforces Constitution Principle I (LLMs Never Compute Business Metrics) and
 * Principle V (Provenance and Citation Discipline).
 * Features sharp institutional sovereign light mode design with Base UI Popover.
 */

import * as React from 'react';
import { MetricProvenance, ProvenanceCitation } from '../state/cockpit-types';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { formatUtcTimestamp } from '@/lib/utils';

interface MetricProvenanceBadgeProps {
  metric: MetricProvenance;
  displayMode?: 'badge' | 'inline' | 'compact';
  className?: string;
}

export function MetricCitationTag({ citation }: { citation: ProvenanceCitation | string }) {
  let badgeColor = 'bg-cx-sub text-cx-ink-soft border-cx-line';
  if (citation === '[BRIEF]') {
    badgeColor = 'bg-cx-info-bg text-cx-accent border-cx-info-line';
  } else if (citation === '[ASSUMPTION]') {
    badgeColor = 'bg-cx-warn-bg text-cx-warn border-cx-warn-line';
  } else if (citation === '[SPIKE]') {
    badgeColor = 'bg-cx-bad-bg text-cx-bad border-cx-bad-line';
  } else if (citation === '[TARGET]') {
    badgeColor = 'bg-cx-ok-bg text-cx-ok border-cx-ok-line';
  } else if (citation === '[ILLUSTRATIVE]') {
    badgeColor = 'bg-cx-sub text-cx-muted border-cx-line';
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.2 text-label font-mono font-medium tracking-tight border rounded-none uppercase ${badgeColor}`}
      title={`Citation type: ${citation}`}
    >
      {citation}
    </span>
  );
}

export function MetricProvenanceBadge({
  metric,
  displayMode = 'inline',
  className = '',
}: MetricProvenanceBadgeProps) {
  const formattedAsOf = React.useMemo(() => formatUtcTimestamp(metric.asOfTimestamp), [metric.asOfTimestamp]);

  return (
    <Popover>
      <PopoverTrigger
        className={`group inline-flex items-center gap-1 cursor-pointer transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-slate-400 ${
          displayMode === 'badge'
            ? 'px-2 py-0.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-900 text-xs font-mono rounded-none'
            : displayMode === 'compact'
            ? 'text-xs text-slate-800 hover:text-slate-950 underline decoration-slate-300 underline-offset-2 font-mono'
            : 'text-sm text-slate-900 font-semibold hover:text-blue-700 border-b border-dotted border-slate-400 pb-0.5'
        } ${className}`}
      >
        <span className="tabular-nums font-mono">{metric.formattedValue}</span>
        {metric.unit && <span className="text-xs text-slate-500 font-normal">{metric.unit}</span>}
        <MetricCitationTag citation={metric.citation} />
        <span
          className="material-symbols-sharp text-[13px] text-slate-400 group-hover:text-blue-600 transition-colors ml-0.5"
          aria-hidden="true"
        >
          verified
        </span>
      </PopoverTrigger>

      <PopoverContent
        align="start"
        sideOffset={6}
        className="w-80 p-0 bg-white border border-slate-200 shadow-xl rounded-none text-slate-900 z-50 animate-in fade-in-0 zoom-in-95 duration-100"
      >
        {/* Institutional Popover Header */}
        <div className="bg-slate-50 border-b border-slate-200 px-3 py-2 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-sharp text-sm text-blue-600">verified</span>
            <span className="text-label font-semibold tracking-wide text-slate-700 uppercase">
              Semantic Provenance
            </span>
          </div>
          <MetricCitationTag citation={metric.citation} />
        </div>

        {/* Metric Value & Name */}
        <div className="px-3 pt-3 pb-2 border-b border-slate-100">
          <div className="text-xs text-slate-500 font-medium">{metric.name}</div>
          <div className="text-lg font-bold font-mono tracking-tight text-slate-900 flex items-baseline gap-1 mt-0.5">
            <span>{metric.formattedValue}</span>
            {metric.unit && <span className="text-xs font-normal text-slate-500">{metric.unit}</span>}
          </div>
        </div>

        {/* Audit Details Grid */}
        <div className="px-3 py-2.5 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Metric ID</span>
            <span className="font-mono font-medium text-slate-900">{metric.metricId}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Semantic Version</span>
            <span className="font-mono text-slate-800 bg-slate-100 px-1 py-0.5 text-label">
              {metric.semanticDefinitionVersion}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Calculation Engine</span>
            <span className="font-mono text-label text-blue-800 bg-blue-50 px-1.5 py-0.5 border border-blue-100">
              {metric.originEngine}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">As-Of Snapshot</span>
            <span className="font-mono text-label text-slate-700">{formattedAsOf}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Business Steward</span>
            <span className="font-medium text-slate-800">{metric.stewardRole}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Live Telemetry</span>
            <span
              className={`inline-flex items-center gap-1 text-label font-mono ${
                metric.isCached ? 'text-amber-700' : 'text-emerald-700'
              }`}
            >
              <span
                className={`inline-block size-1.5 rounded-full ${
                  metric.isCached ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
              />
              {metric.isCached ? 'Cached Snapshot' : 'Real-Time Synchronized'}
            </span>
          </div>
        </div>

        {/* Deterministic Rigor / Principle I Guarantee Footer */}
        <div className="bg-slate-50 border-t border-slate-200 px-3 py-1.5 text-label text-slate-500 flex items-center gap-1 font-mono">
          <span className="material-symbols-sharp text-label text-slate-400">shield</span>
          <span>Principle I: Deterministic semantic layer. Zero LLM calculation.</span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

