'use client';

/**
 * Universal Tripartite Grid Shell
 * Assembles the Common Operational Picture (COP) layout:
 * - Top: Header Navigation & Role Switcher
 * - Full-height left edge: Global Navigation Rail (48px dark icon strip, hover-expands as overlay)
 * - Left: Discrepancy-Ranked Triage Rail (fluid w-72 2xl:w-80, collapsible)
 * - Center: Copilot Operational Dossier (fluid w-[420px] xl:w-[480px] 2xl:w-[540px])
 * - Right: Kinetic Canvas (Flexible min-w-[440px], collapsible)
 * - Bottom: Governed Action Shelf (Two-Phase Commit)
 * - Omnipresent: Copilot Command Bar (Cmd+K) & Keyboard Shortcuts Palette (?)
 * Strict Sovereign Light Mode design system.
 */

import * as React from 'react';
import { HeaderNav } from './header-nav';
import { AppNavRail } from './app-nav-rail';
import { PaneResizer } from './pane-resizer';
import { usePersistedWidth } from './use-persisted-width';

const DOSSIER_DEFAULT_PX = 460;
const DOSSIER_MIN_PX = 320;
const DOSSIER_MAX_PX = 720;
import { TriageRail } from './triage-rail';
import { CopilotDossier } from './copilot-dossier';
import { KineticCanvas } from './kinetic-canvas';
import { GovernedActionShelf } from './governed-action-shelf';
import { CopilotCommandBar } from './copilot-command-bar';
import { KeyboardShortcutsModal } from '../common/keyboard-shortcuts-modal';
import { useCockpit } from '../state/cockpit-context';
import { useForensicUrlSync } from '../state/use-forensic-url-sync';

export function TripartiteShell({
  defaultRailCollapsed = false,
}: {
  defaultRailCollapsed?: boolean;
} = {}) {
  const { setRole } = useCockpit();
  useForensicUrlSync();
  const [leftRailCollapsed, setLeftRailCollapsed] = React.useState(() => {
    if (defaultRailCollapsed) return true;
    if (typeof window !== 'undefined' && window.innerWidth < 768) return true;
    return false;
  });
  const [rightCanvasCollapsed, setRightCanvasCollapsed] = React.useState(false);
  const [shortcutsModalOpen, setShortcutsModalOpen] = React.useState(false);
  const [dossierWidth, setDossierWidth] = usePersistedWidth(
    'eios.pane.dossier',
    DOSSIER_DEFAULT_PX,
    DOSSIER_MIN_PX,
    DOSSIER_MAX_PX,
  );

  // Global Keyboard Shortcuts ([, ], ?, 1-5)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when typing in inputs or textareas
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return;
      }

      if (e.key === '[') {
        e.preventDefault();
        setLeftRailCollapsed((prev) => !prev);
      } else if (e.key === ']') {
        e.preventDefault();
        setRightCanvasCollapsed((prev) => !prev);
      } else if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
        e.preventDefault();
        setShortcutsModalOpen((prev) => !prev);
      } else if (e.key === '1') {
        setRole('executive');
      } else if (e.key === '2') {
        setRole('aml_investigator');
      } else if (e.key === '3') {
        setRole('partner_manager');
      } else if (e.key === '4') {
        setRole('compliance_auditor');
      } else if (e.key === '5') {
        setRole('data_operations');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setRole]);

  return (
    <div data-cockpit-shell className="relative h-screen w-screen flex flex-row bg-cx-canvas text-slate-900 font-sans antialiased overflow-hidden">
      {/* Skip link: first tab stop, jumps past the rail and header controls */}
      <a
        href="#workspace"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById('workspace')?.focus();
        }}
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[60] focus:px-3 focus:py-1.5 focus:bg-cx-ink focus:text-white focus:text-xs focus:font-medium focus:outline-none focus:ring-2 focus:ring-cx-accent"
      >
        Skip to workspace
      </a>

      {/* Global Navigation Rail: permanent 48px dark icon strip, expands on hover as an overlay */}
      <AppNavRail onOpenShortcuts={() => setShortcutsModalOpen(true)} />

      {/* Main column: header, tripartite work area, action shelf */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top Header Bar */}
        <HeaderNav onOpenShortcuts={() => setShortcutsModalOpen(true)} />

        {/* Tripartite COP Center Work Area */}
        <div id="workspace" tabIndex={-1} className="flex-1 flex overflow-hidden relative outline-none">
          {/* Left Triage Rail: fluid (collapsible on smaller displays) */}
          {!leftRailCollapsed ? (
            <div className="flex h-full">
              <TriageRail onCollapse={() => setLeftRailCollapsed(true)} />
            </div>
          ) : (
            <div className="w-8 shrink-0 bg-slate-100 border-r border-slate-300 flex flex-col items-center py-3 select-none">
              <button
                type="button"
                onClick={() => setLeftRailCollapsed(false)}
                className="size-6 bg-white border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-50 cursor-pointer"
                title="Expand Left Rail (press [)"
                aria-label="Expand Left Rail"
              >
                <span className="material-symbols-sharp text-sm">chevron_right</span>
              </button>
              <span className="[writing-mode:vertical-rl] text-label font-mono tracking-wider text-slate-500 uppercase mt-4">
                Triage Signals
              </span>
            </div>
          )}

          {/* Center Copilot Dossier: user-resizable, width remembered */}
          <div style={{ width: dossierWidth }} className="shrink min-w-[300px] h-full flex">
            <CopilotDossier />
          </div>
          <PaneResizer
            label="Resize dossier"
            value={dossierWidth}
            min={DOSSIER_MIN_PX}
            max={DOSSIER_MAX_PX}
            defaultValue={DOSSIER_DEFAULT_PX}
            onChange={setDossierWidth}
          />

          {/* Right Kinetic Canvas: Flexible fill (collapsible) */}
          {!rightCanvasCollapsed ? (
            <div className="flex-1 flex h-full overflow-hidden">
              <KineticCanvas onCollapse={() => setRightCanvasCollapsed(true)} />
            </div>
          ) : (
            <div className="w-8 shrink-0 bg-slate-100 border-l border-slate-300 flex flex-col items-center py-3 select-none">
              <button
                type="button"
                onClick={() => setRightCanvasCollapsed(false)}
                className="size-6 bg-white border border-slate-300 flex items-center justify-center text-slate-700 hover:bg-slate-50 cursor-pointer"
                title="Expand Right Canvas (press ])"
                aria-label="Expand Right Canvas"
              >
                <span className="material-symbols-sharp text-sm">chevron_left</span>
              </button>
              <span className="[writing-mode:vertical-rl] text-label font-mono tracking-wider text-slate-500 uppercase mt-4">
                Kinetic Canvas
              </span>
            </div>
          )}
        </div>

        {/* Governed Action Shelf (Pinned Bottom) */}
        <GovernedActionShelf />
      </div>

      {/* Omnipresent Cmd+K Copilot Dialog */}
      <CopilotCommandBar />

      {/* Power-User Keyboard Shortcuts Modal (?) */}
      <KeyboardShortcutsModal
        isOpen={shortcutsModalOpen}
        onClose={() => setShortcutsModalOpen(false)}
      />
    </div>
  );
}
