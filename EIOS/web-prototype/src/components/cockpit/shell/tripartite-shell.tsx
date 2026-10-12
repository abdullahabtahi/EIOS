'use client';

/**
 * Universal Tripartite Grid Shell
 * Assembles the Common Operational Picture (COP) layout:
 * - Top: Header Navigation & Role Switcher
 * - Left: Discrepancy-Ranked Triage Rail (fluid w-72 2xl:w-80, collapsible)
 * - Center: Copilot Operational Dossier (fluid w-[420px] xl:w-[480px] 2xl:w-[540px])
 * - Right: Kinetic Canvas (Flexible min-w-[440px], collapsible)
 * - Bottom: Governed Action Shelf (Two-Phase Commit)
 * - Omnipresent: Copilot Command Bar (Cmd+K) & Keyboard Shortcuts Palette (?)
 * Strict Sovereign Light Mode design system.
 */

import * as React from 'react';
import { HeaderNav } from './header-nav';
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
    <div className="h-screen w-screen flex flex-col bg-[#f4f6f8] text-slate-900 font-sans antialiased overflow-hidden select-none">
      {/* Top Header Bar */}
      <HeaderNav onOpenShortcuts={() => setShortcutsModalOpen(true)} />

      {/* Tripartite COP Center Work Area */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Triage Rail: fluid (collapsible on smaller displays) */}
        {!leftRailCollapsed ? (
          <div className="flex h-full relative">
            <TriageRail />
            <button
              type="button"
              onClick={() => setLeftRailCollapsed(true)}
              className="absolute right-0 top-2 translate-x-1/2 z-20 size-5 bg-white border border-slate-300 rounded-full shadow-xs flex items-center justify-center text-slate-500 hover:text-slate-900 cursor-pointer hidden lg:flex"
              title="Collapse Left Rail (press [)"
              aria-label="Collapse Left Rail"
            >
              <span className="material-symbols-sharp text-xs">chevron_left</span>
            </button>
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
            <span className="[writing-mode:vertical-rl] text-[10px] font-mono tracking-wider text-slate-500 uppercase mt-4">
              Triage Signals
            </span>
          </div>
        )}

        {/* Center Copilot Dossier: fluid */}
        <CopilotDossier />

        {/* Right Kinetic Canvas: Flexible fill (collapsible) */}
        {!rightCanvasCollapsed ? (
          <div className="flex-1 flex h-full relative overflow-hidden">
            <button
              type="button"
              onClick={() => setRightCanvasCollapsed(true)}
              className="absolute left-0 top-2 -translate-x-1/2 z-20 size-5 bg-white border border-slate-300 rounded-full shadow-xs flex items-center justify-center text-slate-500 hover:text-slate-900 cursor-pointer hidden lg:flex"
              title="Collapse Right Canvas (press ])"
              aria-label="Collapse Right Canvas"
            >
              <span className="material-symbols-sharp text-xs">chevron_right</span>
            </button>
            <KineticCanvas />
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
            <span className="[writing-mode:vertical-rl] text-[10px] font-mono tracking-wider text-slate-500 uppercase mt-4">
              Kinetic Canvas
            </span>
          </div>
        )}
      </div>

      {/* Governed Action Shelf (Pinned Bottom) */}
      <GovernedActionShelf />

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
