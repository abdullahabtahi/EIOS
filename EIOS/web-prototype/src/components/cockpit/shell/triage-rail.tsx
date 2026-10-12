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
import { useKeyboardTriage } from './use-keyboard-triage';

const SEVERITIES: Array<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'> = [
  'ALL',
  'CRITICAL',
  'HIGH',
  'MEDIUM',
  'LOW',
];

export function TriageRail() {
  const {
    state,
    filteredTriageItems,
    selectTriageItem,
    setSearchQuery,
    setSeverityFilter,
  } = useCockpit();

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
            <span className="text-[11px] font-bold font-mono uppercase tracking-wider text-slate-900">
              Triage Signals
            </span>
          </div>
          <div className="flex items-center gap-1">
            <span className="px-1 py-0.2 bg-slate-100 text-slate-600 text-[9px] font-mono border border-slate-300" title="Keyboard hotkeys: j/k move, x select, e hold, f sar">
              j/k/e/f
            </span>
            <span className="px-1.5 py-0.2 bg-slate-200 text-slate-800 text-[10px] font-mono font-bold">
              {filteredTriageItems.length} active
            </span>
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
        <div className="flex items-center gap-1 overflow-x-auto text-[10px] font-mono">
          {SEVERITIES.map((sev) => {
            const isActive = state.triageSeverityFilter === sev;
            return (
              <button
                key={sev}
                type="button"
                onClick={() => setSeverityFilter(sev)}
                className={`px-2 py-0.5 rounded-none border transition-colors cursor-pointer shrink-0 font-mono text-[10px] ${
                  isActive
                    ? 'bg-[#182026] border-[#182026] text-white font-bold'
                    : 'bg-[#F5F8FA] hover:bg-[#EBF1F5] border-[#D8E1E8] text-[#5C7080]'
                }`}
              >
                {sev}
              </button>
            );
          })}
        </div>
      </div>

      {/* Triage Items Scrollable List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin divide-y divide-[#E1E8ED]">
        {filteredTriageItems.length === 0 ? (
          <div className="p-6 text-center text-[#8A9BA8] text-xs">
            <span className="material-symbols-sharp text-2xl text-[#CED9E0] block mb-1">
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
                className={`w-full text-left p-3 border-l-2 border-l-transparent transition-colors cursor-pointer block outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#106BA3] ${
                  isSelected
                    ? 'bg-[#E8F1F8] shadow-[inset_0_1px_0_rgba(16,107,163,0.28),inset_0_-1px_0_rgba(16,107,163,0.28)]'
                    : 'bg-white hover:bg-[#F9FBFC]'
                }`}
              >
                {/* Severity & Score Header */}
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span
                    className={`px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider border ${
                      isCritical
                        ? 'bg-[#FAF0F0] text-[#A82A2A] border-[#E8C5C5]'
                        : isHigh
                        ? 'bg-[#FAF5EC] text-[#A66321] border-[#EAD8B5]'
                        : isMedium
                        ? 'bg-[#F0F4FA] text-[#215DB0] border-[#C7D7EE]'
                        : 'bg-[#F5F8FA] text-[#5C7080] border-[#D8E1E8]'
                    }`}
                  >
                    {item.severity}
                  </span>

                  <span className="text-[10px] font-mono text-[#5C7080] tabular-nums">
                    P={(item.priorityScore ?? 0).toFixed(2)}
                  </span>
                </div>

                {/* Title & Subtitle */}
                <div className={`text-xs font-bold leading-snug truncate ${isSelected ? 'text-[#0E5A8A]' : 'text-[#182026]'}`}>
                  {item.title}
                </div>
                <div className="text-[11px] text-[#5C7080] truncate mt-0.5 leading-normal">
                  {item.subtitle}
                </div>

                {/* Entity ID & Metric Pills (Entity Tag) */}
                <div className="mt-2 flex items-center justify-between gap-1 text-[10px] font-mono">
                  <span className="text-[#394B59] bg-[#F5F8FA] px-1.5 py-0.5 border border-[#D8E1E8] font-medium tracking-tight truncate uppercase">
                    {item.entityId}
                  </span>

                  {item.metricsSummary &&
                    Object.entries(item.metricsSummary).slice(0, 1).map(([key, val]) => (
                      <span key={key} className="text-[#182026] font-semibold truncate tabular-nums">
                        {String(val)}
                      </span>
                    ))}
                </div>

                {/* Tags */}
                {(item.tags ?? []).length > 0 && (
                  <div className="flex items-center gap-1 mt-1.5 overflow-hidden">
                    {(item.tags ?? []).map((tag) => (
                      <span
                        key={tag}
                        className="text-[9px] font-mono text-[#8A9BA8] bg-[#F5F8FA] px-1 py-0.2"
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
