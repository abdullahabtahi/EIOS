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
import { SystemStatusDialog } from '../common/system-status-dialog';
import { getPipelineStatus, type PipelineTone } from '../state/pipeline-status';
import { useAuth } from '@/lib/auth/auth-context';

const ENV_LABEL = process.env.NEXT_PUBLIC_EIOS_ENV ?? 'DEMO';

const TONE_DOT: Record<PipelineTone, string> = {
  ok: 'bg-emerald-400',
  warn: 'bg-amber-400',
  bad: 'bg-red-400',
  neutral: 'bg-slate-400',
};
const TONE_TEXT: Record<PipelineTone, string> = {
  ok: 'text-emerald-400',
  warn: 'text-amber-300',
  bad: 'text-red-300',
  neutral: 'text-slate-300',
};

const KBD = 'px-1 py-0.5 bg-white/8 border border-white/15 text-label font-mono text-slate-300';

export function HeaderNav({
  onOpenShortcuts,
}: {
  onOpenShortcuts?: () => void;
} = {}) {
  const { status: authStatus, operator: authOperator, signOutOperator } = useAuth();
  const { state, setRole, setCopilotCommandOpen } = useCockpit();
  const pipeline = getPipelineStatus(state);
  const [statusOpen, setStatusOpen] = React.useState(false);

  return (
    <header className="w-full bg-white border-b border-slate-200 select-none z-30 shrink-0 shadow-2xs">
      {/* Top Utility & Identity Bar */}
      <div className="h-11 px-4 flex items-center justify-between bg-cockpit-rail text-slate-100">
        {/* Left Branding */}
        <div className="flex items-center gap-3">
          <div className="flex items-baseline gap-1.5">
            <span className="font-mono font-bold tracking-widest text-xs text-white uppercase">EIOS</span>
            <span className="text-label text-slate-400 font-mono tracking-wider uppercase hidden sm:inline">
              / OPERATOR COCKPIT v2.4
            </span>
          </div>
          <span className="px-1.5 py-0.5 bg-white/8 border border-white/15 text-slate-200 font-mono text-label font-bold tracking-wider">
            {ENV_LABEL} • TLP:AMBER
          </span>
        </div>

        {/* Center / Right Telemetry & Controls */}
        <div className="flex items-center gap-2.5">
          {/* Telemetry Lag & Latency */}
          <button
            type="button"
            data-testid="header-pipeline-status"
            aria-haspopup="dialog"
            title="System status"
            onClick={() => setStatusOpen(true)}
            className="flex items-center gap-2 text-label font-mono text-slate-300 bg-white/5 hover:bg-white/10 px-2.5 py-1 border border-chrome-line cursor-pointer transition-colors outline-none focus-visible:ring-2 focus-visible:ring-chrome-accent"
          >
            <span className="flex items-center gap-1">
              <span className={`size-1.5 rounded-full inline-block ${TONE_DOT[pipeline.tone]}`} />
              <span className="text-slate-400 hidden lg:inline">Pipeline:</span>
              <span className={`${TONE_TEXT[pipeline.tone]} font-semibold`}>{pipeline.label}</span>
            </span>
            <span className="hidden lg:contents">
              <span className="text-slate-600">|</span>
              <span className="flex items-center gap-1">
                <span className="text-slate-400">RTT:</span>
                <span className="text-white font-semibold tabular-nums">
                  {pipeline.label === 'Replay' ? '—' : `${state.systemLatencyMs}ms`}
                </span>
              </span>
              <span className="text-slate-600">|</span>
              <span className="flex items-center gap-1" title={state.asOfTimestamp}>
                <span className="text-slate-400">As of:</span>
                <span className="text-slate-100 font-semibold tabular-nums">
                  {state.asOfTimestamp ? `${state.asOfTimestamp.slice(0, 16).replace('T', ' ')} UTC` : '—'}
                </span>
              </span>
            </span>
            <span className="material-symbols-sharp text-sm text-slate-400">expand_more</span>
          </button>
          <SystemStatusDialog open={statusOpen} onOpenChange={setStatusOpen} />

          {/* Omnipresent Copilot Trigger (Cmd+K) */}
          <button
            type="button"
            onClick={() => setCopilotCommandOpen(true)}
            className="flex items-center gap-2 px-2.5 py-1 bg-white/5 hover:bg-white/10 border border-white/15 text-slate-100 text-xs font-medium rounded-none transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-chrome-accent"
            title="Open Copilot Command Bar (Cmd+K)"
          >
            <span className="material-symbols-sharp text-sm text-chrome-accent">terminal</span>
            <span className="hidden md:inline text-label font-mono">Command Bar</span>
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
            <div className="size-6 bg-white/10 border border-white/15 text-white flex items-center justify-center font-mono font-bold text-label">
              {(authOperator?.email ?? state.operator.officerId).slice(0, 2).toUpperCase()}
            </div>
            <div className="hidden xl:block text-left">
              <div className="text-label font-bold text-white leading-tight">
                {authOperator?.email ?? state.operator.name}
              </div>
              <div className="text-label font-mono text-slate-400 leading-tight uppercase tracking-wider">
                {authOperator?.role ?? state.operator.clearanceLevel.replace(/_/g, ' ')}
              </div>
            </div>
            {authStatus === 'signedIn' && (
              <button
                type="button"
                onClick={() => void signOutOperator()}
                className="ml-1 px-2 py-1 border border-white/15 text-label font-mono uppercase tracking-wider text-slate-300 hover:bg-white/10"
              >
                Sign out
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Role Navigation Tabs Strip */}
      <nav aria-label="Workstation Persona Switcher" className="h-10 px-4 bg-slate-50/70 border-b border-slate-200 flex items-center gap-1 overflow-x-auto">
        <span aria-hidden="true" className="text-label font-mono uppercase tracking-wider text-slate-500 mr-2 shrink-0">
          Workstation:
        </span>
        <div role="tablist" aria-label="Workstations" className="flex items-stretch h-full gap-1">
          {WORKSTATION_ROLES.map((role, index) => {
            const isActive = state.activeRole === role.id;
            const move = (to: number) => {
              const next = WORKSTATION_ROLES[(to + WORKSTATION_ROLES.length) % WORKSTATION_ROLES.length];
              setRole(next.id);
              document.getElementById(`tab-${next.id}`)?.focus();
            };
            return (
              <button
                key={role.id}
                id={`tab-${role.id}`}
                data-testid={`tab-${role.id}`}
                role="tab"
                type="button"
                aria-selected={isActive}
                aria-controls="workstation-panel"
                tabIndex={isActive ? 0 : -1}
                onClick={() => setRole(role.id)}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowRight') move(index + 1);
                  else if (e.key === 'ArrowLeft') move(index - 1);
                  else if (e.key === 'Home') move(0);
                  else if (e.key === 'End') move(WORKSTATION_ROLES.length - 1);
                  else return;
                  e.preventDefault();
                }}
                className={`h-full px-3.5 text-xs font-medium tracking-tight flex items-center gap-2 transition-colors border-b-2 cursor-pointer shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent ${
                  isActive
                    ? 'border-cx-accent text-cx-accent bg-white font-semibold shadow-2xs'
                    : 'border-transparent text-slate-600 hover:text-slate-950 hover:bg-slate-100/70'
                }`}
              >
                <span aria-hidden="true" className={`material-symbols-sharp text-sm ${isActive ? 'text-cx-accent' : 'text-slate-400'}`}>
                  {role.icon}
                </span>
                <span>{role.label}</span>
                <kbd aria-hidden="true" className="hidden lg:inline text-label font-mono text-slate-500 px-1 py-0.2 bg-slate-100 border border-slate-200">
                  {role.shortcut}
                </kbd>
              </button>
            );
          })}
        </div>
      </nav>

      {/* Replay Banner when Partitioned or Outage Active */}
      <FallbackReplayBanner />
    </header>
  );
}
