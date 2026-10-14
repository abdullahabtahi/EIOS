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
  // Citation type is a category, not a state: one neutral outline for every tag.
  const badgeColor = 'bg-cx-sub text-cx-ink-soft border-cx-line';

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.2 text-label font-mono font-medium tracking-tight border rounded-none uppercase ${badgeColor}`}
      title={`Citation type: ${citation}`}
    >
      {citation}
    </span>
  );
}

/** Citations that name no regime: the figure stays clean and its popover says where it came from. */
const QUIET_CITATIONS: ReadonlySet<string> = new Set(['[ILLUSTRATIVE]', '[COMPUTED]']);

/** What the figure's origin is, from the backend's own word. Unknown is never shown as live. */
function originText(metric: MetricProvenance): string {
  if (metric.dataOrigin === 'fixture') return 'Demo data (fixture)';
  if (metric.dataOrigin === 'engine') return 'Computed by the engines';
  if (metric.dataOrigin === 'live') return 'Live data';
  return metric.isCached ? 'Cached snapshot' : 'Origin not stated';
}

function originTone(metric: MetricProvenance): string {
  if (metric.dataOrigin === 'live' || metric.dataOrigin === 'engine') return 'text-green-700';
  if (metric.dataOrigin === 'fixture' || metric.isCached) return 'text-amber-700';
  return 'text-slate-500';
}

/** One label and value; a long value (an id, a code path) wraps inside the popover instead of spilling out. */
function PopoverRow({ label, mono = false, children }: { label: string; mono?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-slate-500 shrink-0">{label}</span>
      <span className={`min-w-0 text-right break-all text-slate-800 ${mono ? 'font-mono text-label' : 'font-medium'}`}>
        {children}
      </span>
    </div>
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
        {/* An assistant figure's text already carries its unit and sign; only legacy citations show the unit apart. */}
        {metric.unit && metric.dataOrigin === undefined && (
          <span className="text-xs text-slate-500 font-normal">{metric.unit}</span>
        )}
        {/* The figure itself stays clean; the citation type and data origin are in the popover. */}
        {!QUIET_CITATIONS.has(metric.citation) && <MetricCitationTag citation={metric.citation} />}
        {/* A tick only when the figure names where it came from. */}
        {metric.originEngine && (
          <span
            className="material-symbols-sharp text-[13px] text-slate-400 group-hover:text-blue-600 transition-colors ml-0.5"
            aria-hidden="true"
          >
            verified
          </span>
        )}
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
          {!QUIET_CITATIONS.has(metric.citation) && <MetricCitationTag citation={metric.citation} />}
        </div>

        {/* Metric Value & Name */}
        <div className="px-3 pt-3 pb-2 border-b border-slate-100">
          <div className="text-xs text-slate-500 font-medium">{metric.name}</div>
          <div className="text-lg font-bold font-mono tracking-tight text-slate-900 flex items-baseline gap-1 mt-0.5">
            <span>{metric.formattedValue}</span>
            {metric.unit && metric.dataOrigin === undefined && (
              <span className="text-xs font-normal text-slate-500">{metric.unit}</span>
            )}
          </div>
        </div>

        {/* Audit Details Grid */}
        <div className="px-3 py-2.5 space-y-2 text-xs">
          <PopoverRow label="Metric ID" mono>
            {metric.metricId}
          </PopoverRow>
          {metric.semanticDefinitionVersion && (
            <PopoverRow label="Semantic Version" mono>
              {metric.semanticDefinitionVersion}
            </PopoverRow>
          )}
          {metric.originEngine && (
            <PopoverRow label="Calculation Engine" mono>
              {metric.originEngine}
            </PopoverRow>
          )}
          <PopoverRow label="As-Of Snapshot" mono>
            {formattedAsOf}
          </PopoverRow>
          {metric.stewardRole && metric.stewardRole !== metric.originEngine && (
            <PopoverRow label="Business Steward">{metric.stewardRole}</PopoverRow>
          )}
          <PopoverRow label="Data origin">
            <span className={`font-mono ${originTone(metric)}`}>{originText(metric)}</span>
          </PopoverRow>
        </div>
      </PopoverContent>
    </Popover>
  );
}

