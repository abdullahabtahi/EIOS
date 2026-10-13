'use client';

/**
 * Left Triage Rail (300px Fixed Column)
 * Universal Tripartite COP Left Zone.
 * Displays discrepancy-ranked operational triage items, priority scores,
 * severity tags, search filter, and selection dispatch.
 * Strict Institutional Light-Mode styling.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { countBySeverity, formatAge } from '../state/triage-meta';
import { Chip, type ChipTone } from '../ui/chip';
import { useKeyboardTriage } from './use-keyboard-triage';

const SEVERITIES: Array<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'> = [
  'ALL',
  'CRITICAL',
  'HIGH',
  'MEDIUM',
  'LOW',
];

const PILL_LABEL: Record<string, string> = { ALL: 'ALL', CRITICAL: 'CRIT', HIGH: 'HIGH', MEDIUM: 'MED', LOW: 'LOW' };

const STATUS_TONE: Record<string, ChipTone> = {
  OPEN: 'neutral',
  INVESTIGATING: 'info',
  STAGED: 'warn',
  RESOLVED: 'ok',
  DISMISSED: 'neutral',
};

export function TriageRail({ onCollapse }: { onCollapse?: () => void } = {}) {
  const {
    state,
    filteredTriageItems,
    selectTriageItem,
    setSearchQuery,
    setSeverityFilter,
  } = useCockpit();

  // Counts reflect the text search but not the severity filter, so every pill stays meaningful.
  const counts = React.useMemo(() => {
    const q = state.triageSearchQuery.trim().toLowerCase();
    const searched = q
      ? state.triageItems.filter((i) =>
          [i.title, i.subtitle, i.entityId, ...i.tags].some((t) => t.toLowerCase().includes(q)),
        )
      : state.triageItems;
    return countBySeverity(searched);
  }, [state.triageItems, state.triageSearchQuery]);

  // Mount keyboard velocity navigation (j/k/x/e/f)
  useKeyboardTriage(filteredTriageItems);

  return (
    <aside
      aria-label="Triage Queue Rail"
      className="w-72 2xl:w-80 shrink-0 bg-white border-r border-slate-200 flex flex-col h-full select-none"
    >
      {/* Rail Top Header */}
      <div className="p-3 bg-slate-50 border-b border-slate-200 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-sharp text-sm text-slate-700">playlist_play</span>
            <span className="text-label font-bold font-mono uppercase tracking-wider text-slate-900">
              Triage Signals
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="px-1.5 py-0.2 bg-slate-200 text-slate-800 text-label font-mono font-bold whitespace-nowrap" title="Keyboard: j/k move, x select, e hold, f file SAR">
              {filteredTriageItems.length} active
            </span>
            {onCollapse && (
              <button
                type="button"
                onClick={onCollapse}
                title="Collapse Left Rail (press [)"
                aria-label="Collapse Left Rail"
                className="ml-1 size-6 flex items-center justify-center text-slate-500 hover:text-slate-900 hover:bg-slate-200 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-cx-accent"
              >
                <span className="material-symbols-sharp text-base">chevron_left</span>
              </button>
            )}
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <span className="material-symbols-sharp absolute left-2 top-2 text-slate-400 text-sm">
            filter_list
          </span>
          <input
            type="text"
            value={state.triageSearchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter triage queue..."
            className="w-full pl-7 pr-2 py-1.5 text-xs bg-white border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 rounded-none font-sans"
          />
        </div>

        {/* Severity Filter Pills */}
        <div className="flex items-center gap-1 overflow-x-auto text-label font-mono">
          {SEVERITIES.map((sev) => {
            const isActive = state.triageSeverityFilter === sev;
            const count = counts[sev as keyof typeof counts];
            return (
              <button
                key={sev}
                type="button"
                aria-label={`${sev} ${count}`}
                title={`${sev}: ${count}`}
                aria-pressed={isActive}
                onClick={() => setSeverityFilter(sev)}
                className={`min-h-6 px-1.5 py-0.5 rounded-none border transition-colors cursor-pointer shrink-0 font-mono text-label flex items-center gap-1.5 ${
                  isActive
                    ? 'bg-cx-ink border-cx-ink text-white font-bold'
                    : count === 0
                    ? 'bg-cx-sub border-cx-line text-cx-faint'
                    : 'bg-cx-sub hover:bg-cx-sub-2 border-cx-line text-cx-muted'
                }`}
              >
                <span aria-hidden="true">{PILL_LABEL[sev]}</span>
                <span aria-hidden="true" className="tabular-nums opacity-80">{count}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Triage Items Scrollable List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin divide-y divide-cx-line-soft">
        {filteredTriageItems.length === 0 ? (
          <div className="p-6 text-center text-cx-faint text-xs">
            <span className="material-symbols-sharp text-2xl text-cx-line-strong block mb-1">
              search_off
            </span>
            No signals match current filters.
          </div>
        ) : (
          filteredTriageItems.map((item) => {
            const isSelected = state.activeTriageItemId === item.id;
            const isCritical = item.severity === 'CRITICAL';
            const isHigh = item.severity === 'HIGH';
            const isMedium = item.severity === 'MEDIUM';

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => selectTriageItem(item.id)}
                aria-current={isSelected ? 'true' : undefined}
                className={`w-full text-left p-3 border-l-2 border-l-transparent transition-colors cursor-pointer block outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent ${
                  isSelected
                    ? 'bg-cx-select shadow-[inset_0_1px_0_rgba(16,107,163,0.28),inset_0_-1px_0_rgba(16,107,163,0.28)]'
                    : 'bg-white hover:bg-cx-hover'
                }`}
              >
                {/* Severity & Score Header */}
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span
                    className={`px-1.5 py-0.5 text-label font-mono font-bold uppercase tracking-wider border ${
                      isCritical
                        ? 'bg-cx-bad-bg text-cx-bad border-cx-bad-line'
                        : isHigh
                        ? 'bg-cx-warn-bg text-cx-warn border-cx-warn-line'
                        : isMedium
                        ? 'bg-cx-info-bg-2 text-cx-info border-cx-info-line-2'
                        : 'bg-cx-sub text-cx-muted border-cx-line'
                    }`}
                  >
                    {item.severity}
                  </span>

                  <span className="text-label font-mono text-cx-muted tabular-nums">
                    P={(item.priorityScore ?? 0).toFixed(2)}
                  </span>
                </div>

                {/* Title & Subtitle */}
                <div className={`text-xs font-bold leading-snug truncate ${isSelected ? 'text-cx-accent-strong' : 'text-cx-ink'}`}>
                  {item.title}
                </div>
                <div className="text-label text-cx-muted truncate mt-0.5 leading-normal">
                  {item.subtitle}
                </div>

                {/* Entity tag (left); lifecycle status + age relative to the data as-of time (right) */}
                <div className="mt-2 flex items-center justify-between gap-2 text-label font-mono">
                  <span className="text-cx-ink-soft bg-cx-sub px-1.5 py-0.5 border border-cx-line font-medium tracking-tight truncate uppercase">
                    {item.entityId}
                  </span>
                  <span className="flex items-center gap-1.5 shrink-0 text-cx-muted">
                    {item.status !== 'OPEN' && <Chip tone={STATUS_TONE[item.status] ?? 'neutral'}>{item.status}</Chip>}
                    <span title={`Raised ${item.timestamp}`} className="tabular-nums">
                      {formatAge(item.timestamp, state.asOfTimestamp)}
                    </span>
                  </span>
                </div>

                {/* Tags */}
                {(item.tags ?? []).length > 0 && (
                  <div className="flex items-center gap-1 mt-1.5 overflow-hidden">
                    {(item.tags ?? []).map((tag) => (
                      <span
                        key={tag}
                        className="text-label font-mono text-cx-faint bg-cx-sub px-1 py-0.2"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}
