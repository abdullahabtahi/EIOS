'use client';

/**
 * Institutional Operator Cockpit Header Navigation (dark global chrome)
 * Hosts Persona Role Switcher, System Telemetry, Ingestion Lag Indicator,
 * Deterministic Outage Simulation Toggle, and Operator Identity.
 * The first row is dark and, with the left navigation rail, frames the Sovereign
 * Light workspace; the persona strip below it stays light. The brand tile lives in the rail.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { WORKSTATION_ROLES } from './workstation-roles';
import { FallbackReplayBanner } from '../common/fallback-replay-badge';

const KBD = 'px-1 py-0.5 bg-white/8 border border-white/15 text-[10px] font-mono text-slate-300';

export function HeaderNav({
  onOpenShortcuts,
}: {
  onOpenShortcuts?: () => void;
} = {}) {
  const { state, setRole, setCopilotCommandOpen } = useCockpit();

  return (
    <header className="w-full bg-white border-b border-slate-200 select-none z-30 shrink-0 shadow-2xs">
      {/* Top Utility & Identity Bar */}
      <div className="h-11 px-4 flex items-center justify-between bg-cockpit-rail text-slate-100">
        {/* Left Branding */}
        <div className="flex items-center gap-3">
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono font-bold tracking-widest text-xs text-white uppercase">EIOS</span>
            <span className="text-[10px] text-slate-400 font-mono tracking-wider uppercase hidden sm:inline">
              / OPERATOR COCKPIT v2.4
            </span>
          </div>
          <span className="px-1.5 py-0.5 bg-white/8 border border-white/15 text-slate-200 font-mono text-[9px] font-bold tracking-wider">
            PROD • TLP:AMBER
          </span>
        </div>

        {/* Center / Right Telemetry & Controls */}
        <div className="flex items-center gap-2.5">
          {/* Telemetry Lag & Latency */}
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-slate-300 bg-white/5 px-2.5 py-1 border border-chrome-line">
            <span className="flex items-center gap-1">
              <span className="size-1.5 rounded-full bg-emerald-400 inline-block" />
              <span className="text-slate-400">Pipeline:</span>
              <span className="text-emerald-400 font-semibold">Synced</span>
            </span>
            <span className="text-slate-600">|</span>
            <span className="flex items-center gap-1">
              <span className="text-slate-400">Lag:</span>
              <span className="text-slate-100 font-semibold tabular-nums">18.4s</span>
            </span>
            <span className="text-slate-600">|</span>
            <span className="flex items-center gap-1">
              <span className="text-slate-400">RTT:</span>
              <span className="text-white font-semibold tabular-nums">{state.systemLatencyMs}ms</span>
            </span>
          </div>

          {/* Omnipresent Copilot Trigger (Cmd+K) */}
          <button
            type="button"
            onClick={() => setCopilotCommandOpen(true)}
            className="flex items-center gap-2 px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-white/15 text-slate-100 text-xs font-medium rounded-none transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-chrome-accent"
            title="Open Copilot Command Bar (Cmd+K)"
          >
            <span className="material-symbols-sharp text-sm text-chrome-accent">terminal</span>
            <span className="hidden md:inline text-[11px] font-mono">Command Bar</span>
            <kbd className={KBD}>⌘K</kbd>
          </button>

          {/* Keyboard Shortcuts Trigger (?) */}
          {onOpenShortcuts && (
            <button
              type="button"
              onClick={onOpenShortcuts}
              className="size-7 flex items-center justify-center bg-white/5 hover:bg-white/10 border border-white/15 text-slate-200 text-xs font-mono rounded-none cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-chrome-accent"
              title="Keyboard Shortcuts Palette (?)"
              aria-label="Keyboard Shortcuts"
            >
              <kbd className="font-mono font-bold">?</kbd>
            </button>
          )}

          {/* Current Operator Badge */}
          <div className="flex items-center gap-2 pl-2 border-l border-chrome-line">
            <div className="size-6 bg-white/10 border border-white/15 text-white flex items-center justify-center font-mono font-bold text-[10px]">
              {state.operator.officerId.slice(0, 2)}
            </div>
            <div className="hidden xl:block text-left">
              <div className="text-[11px] font-bold text-white leading-tight">
                {state.operator.name}
              </div>
              <div className="text-[9px] font-mono text-slate-400 leading-tight uppercase tracking-wider">
                {state.operator.clearanceLevel.replace(/_/g, ' ')}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Role Navigation Tabs Strip */}
      <nav aria-label="Workstation Persona Switcher" className="h-10 px-4 bg-slate-50/70 border-b border-slate-200 flex items-center gap-1 overflow-x-auto">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mr-2 shrink-0">
          Workstation:
        </span>
        {WORKSTATION_ROLES.map((role) => {
          const isActive = state.activeRole === role.id;
          return (
            <button
              key={role.id}
              id={`tab-${role.id}`}
              data-testid={`tab-${role.id}`}
              role="tab"
              aria-selected={isActive}
              type="button"
              onClick={() => setRole(role.id)}
              className={`h-full px-3.5 text-xs font-medium tracking-tight flex items-center gap-2 transition-colors border-b-2 cursor-pointer shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#106BA3] ${
                isActive
                  ? 'border-[#106BA3] text-[#106BA3] bg-white font-semibold shadow-2xs'
                  : 'border-transparent text-slate-600 hover:text-slate-950 hover:bg-slate-100/70'
              }`}
            >
              <span className={`material-symbols-sharp text-sm ${isActive ? 'text-[#106BA3]' : 'text-slate-400'}`}>
                {role.icon}
              </span>
              <span>{role.label}</span>
              <kbd className="hidden lg:inline text-[9px] font-mono text-slate-500 px-1 py-0.2 bg-slate-100 border border-slate-200">
                {role.shortcut}
              </kbd>
            </button>
          );
        })}
      </nav>

      {/* Replay Banner when Partitioned or Outage Active */}
      <FallbackReplayBanner />
    </header>
  );
}
