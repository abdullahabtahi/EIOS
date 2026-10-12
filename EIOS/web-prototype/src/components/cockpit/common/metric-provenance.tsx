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

interface MetricProvenanceBadgeProps {
  metric: MetricProvenance;
  displayMode?: 'badge' | 'inline' | 'compact';
  className?: string;
}

export function MetricCitationTag({ citation }: { citation: ProvenanceCitation | string }) {
  let badgeColor = 'bg-[#F5F8FA] text-[#394B59] border-[#D8E1E8]';
  if (citation === '[BRIEF]') {
    badgeColor = 'bg-[#EDF5FA] text-[#106BA3] border-[#BFD3E6]';
  } else if (citation === '[ASSUMPTION]') {
    badgeColor = 'bg-[#FAF5EC] text-[#A66321] border-[#EAD8B5]';
  } else if (citation === '[SPIKE]') {
    badgeColor = 'bg-[#FAF0F0] text-[#A82A2A] border-[#E8C5C5]';
  } else if (citation === '[TARGET]') {
    badgeColor = 'bg-[#EDF7ED] text-[#0D8050] border-[#C3E6D0]';
  } else if (citation === '[ILLUSTRATIVE]') {
    badgeColor = 'bg-[#F5F8FA] text-[#5C7080] border-[#D8E1E8]';
  }

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.2 text-[10px] font-mono font-medium tracking-tight border rounded-none uppercase ${badgeColor}`}
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
  const formattedAsOf = React.useMemo(() => {
    try {
      return new Date(metric.asOfTimestamp).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    } catch {
      return metric.asOfTimestamp;
    }
  }, [metric.asOfTimestamp]);

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
            <span className="text-[11px] font-semibold tracking-wide text-slate-700 uppercase">
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
            <span className="font-mono text-slate-800 bg-slate-100 px-1 py-0.5 text-[11px]">
              {metric.semanticDefinitionVersion}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Calculation Engine</span>
            <span className="font-mono text-[11px] text-blue-800 bg-blue-50 px-1.5 py-0.5 border border-blue-100">
              {metric.originEngine}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">As-Of Snapshot</span>
            <span className="font-mono text-[11px] text-slate-700">{formattedAsOf}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Business Steward</span>
            <span className="font-medium text-slate-800">{metric.stewardRole}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-500">Live Telemetry</span>
            <span
              className={`inline-flex items-center gap-1 text-[11px] font-mono ${
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
        <div className="bg-slate-50 border-t border-slate-200 px-3 py-1.5 text-[10px] text-slate-500 flex items-center gap-1 font-mono">
          <span className="material-symbols-sharp text-[11px] text-slate-400">shield</span>
          <span>Principle I: Deterministic semantic layer. Zero LLM calculation.</span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export const ProvenancePopover = MetricProvenanceBadge;
