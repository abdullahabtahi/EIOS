'use client';

/**
 * Institutional Operator Cockpit Header Navigation
 * Hosts Persona Role Switcher, System Telemetry, Ingestion Lag Indicator,
 * Deterministic Outage Simulation Toggle, and Operator Identity.
 * Strict Sovereign Light Mode design system.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { PersonaRole } from '../state/cockpit-types';
import { FallbackReplayBanner } from '../common/fallback-replay-badge';

const ROLES: { id: PersonaRole; label: string; icon: string; shortcut: string }[] = [
  { id: 'executive', label: 'Executive', icon: 'monitoring', shortcut: '1' },
  { id: 'aml_investigator', label: 'AML Investigator', icon: 'security', shortcut: '2' },
  { id: 'partner_manager', label: 'Partner Manager', icon: 'hub', shortcut: '3' },
  { id: 'compliance_auditor', label: 'Compliance & Audit', icon: 'verified_user', shortcut: '4' },
  { id: 'data_operations', label: 'Data Operations', icon: 'tune', shortcut: '5' },
];

export function HeaderNav({
  onOpenShortcuts,
}: {
  onOpenShortcuts?: () => void;
} = {}) {
  const { state, setRole, setCopilotCommandOpen } = useCockpit();

  return (
    <header className="w-full bg-white border-b border-slate-200 text-slate-900 select-none z-30 shrink-0 shadow-2xs">
      {/* Top Utility & Identity Bar */}
      <div className="h-11 px-4 flex items-center justify-between border-b border-slate-200 bg-white">
        {/* Left Branding: EIOS */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="size-6 bg-slate-900 text-white flex items-center justify-center font-mono font-bold text-xs tracking-tight">
              E
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono font-bold tracking-widest text-xs text-slate-950 uppercase">
                EIOS
              </span>
              <span className="text-[10px] text-slate-500 font-mono tracking-wider uppercase hidden sm:inline">
                / OPERATOR COCKPIT v2.4
              </span>
            </div>
          </div>
          <span className="px-1.5 py-0.5 bg-slate-100 border border-slate-300 text-slate-700 font-mono text-[9px] font-bold tracking-wider">
            PROD • TLP:AMBER
          </span>
        </div>

        {/* Center / Right Telemetry & Controls */}
        <div className="flex items-center gap-2.5">
          {/* Telemetry Lag & Latency */}
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-slate-700 bg-slate-50 px-2.5 py-1 border border-slate-200">
            <span className="flex items-center gap-1">
              <span className="size-1.5 rounded-full bg-emerald-600 inline-block" />
              <span className="text-slate-500">Pipeline:</span>
              <span className="text-emerald-700 font-semibold">Synced</span>
            </span>
            <span className="text-slate-300">|</span>
            <span className="flex items-center gap-1">
              <span className="text-slate-500">Lag:</span>
              <span className="text-slate-800 font-semibold tabular-nums">18.4s</span>
            </span>
            <span className="text-slate-300">|</span>
            <span className="flex items-center gap-1">
              <span className="text-slate-500">RTT:</span>
              <span className="text-slate-900 font-semibold tabular-nums">{state.systemLatencyMs}ms</span>
            </span>
          </div>

          {/* Omnipresent Copilot Trigger (Cmd+K) */}
          <button
            type="button"
            onClick={() => setCopilotCommandOpen(true)}
            className="flex items-center gap-2 px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 text-xs font-medium rounded-none transition-colors cursor-pointer shadow-2xs"
            title="Open Copilot Command Bar (Cmd+K)"
          >
            <span className="material-symbols-sharp text-sm text-[#106BA3]">terminal</span>
            <span className="hidden md:inline text-[11px] font-mono">Command Bar</span>
            <kbd className="px-1 py-0.2 bg-slate-100 border border-slate-300 text-[10px] font-mono text-slate-600 shadow-2xs">
              ⌘K
            </kbd>
          </button>

          {/* Keyboard Shortcuts Trigger (?) */}
          {onOpenShortcuts && (
            <button
              type="button"
              onClick={onOpenShortcuts}
              className="size-7 flex items-center justify-center bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 text-xs font-mono rounded-none cursor-pointer transition-colors shadow-2xs"
              title="Keyboard Shortcuts Palette (?)"
              aria-label="Keyboard Shortcuts"
            >
              <kbd className="font-mono font-bold text-slate-700">?</kbd>
            </button>
          )}

          {/* Current Operator Badge */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
            <div className="size-6 bg-slate-900 text-white flex items-center justify-center font-mono font-bold text-[10px]">
              {state.operator.officerId.slice(0, 2)}
            </div>
            <div className="hidden xl:block text-left">
              <div className="text-[11px] font-bold text-slate-900 leading-tight">
                {state.operator.name}
              </div>
              <div className="text-[9px] font-mono text-slate-500 leading-tight uppercase tracking-wider">
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
        {ROLES.map((role) => {
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
              className={`h-full px-3.5 text-xs font-medium tracking-tight flex items-center gap-2 transition-all border-b-2 cursor-pointer shrink-0 ${
                isActive
                  ? 'border-[#106BA3] text-[#106BA3] bg-white font-semibold shadow-2xs'
                  : 'border-transparent text-slate-600 hover:text-slate-950 hover:bg-slate-100/70'
              }`}
            >
              <span className={`material-symbols-sharp text-sm ${isActive ? 'text-[#106BA3]' : 'text-slate-400'}`}>
                {role.icon}
              </span>
              <span>{role.label}</span>
              <kbd className="hidden lg:inline text-[9px] font-mono text-slate-400 px-1 py-0.2 bg-slate-100 border border-slate-200">
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
