'use client';

/**
 * Institutional Operator Keyboard Shortcuts Palette
 * Displays full keybindings for power operators with institutional precision.
 * Dismissible via Escape or backdrop click.
 */

import * as React from 'react';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SHORTCUT_GROUPS = [
  {
    category: 'Operational Navigation',
    shortcuts: [
      { key: '1', description: 'Switch to Executive Workstation' },
      { key: '2', description: 'Switch to AML Investigator Workstation' },
      { key: '3', description: 'Switch to Partner Manager Workstation' },
      { key: '4', description: 'Switch to Compliance & Audit Workstation' },
      { key: '5', description: 'Switch to Data Operations Workstation' },
    ],
  },
  {
    category: 'Spatial & Canvas Controls',
    shortcuts: [
      { key: '[', description: 'Toggle Left Triage Rail (Collapse / Expand)' },
      { key: ']', description: 'Toggle Right Kinetic Canvas (Collapse / Expand)' },
      { key: '⌘ K', description: 'Open Copilot Conversational Command Bar' },
      { key: '?', description: 'Open Keyboard Shortcuts Palette' },
      { key: 'Esc', description: 'Dismiss active dialog or modal' },
    ],
  },
  {
    category: 'Governance & Staged Actions',
    shortcuts: [
      { key: 'Alt + S', description: 'Stage active trade-off countermeasure to shelf' },
      { key: 'Alt + A', description: 'Open Four-Eyes Dual Authorization modal' },
    ],
  },
];

export function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard Shortcuts Palette"
      className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-[2px] flex items-center justify-center p-4 select-none"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-white border border-slate-300 shadow-xl rounded-none flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base text-[#106BA3]">keyboard</span>
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-900">
              Institutional Operator Keybindings
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 cursor-pointer p-0.5"
            aria-label="Close"
          >
            <span className="material-symbols-sharp text-sm">close</span>
          </button>
        </div>

        {/* Shortcuts Body */}
        <div className="p-4 space-y-4 max-h-[70vh] overflow-y-auto scrollbar-thin">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.category} className="space-y-2">
              <h4 className="text-[10px] font-mono font-bold tracking-wider uppercase text-slate-500 border-b border-slate-100 pb-1">
                {group.category}
              </h4>
              <div className="space-y-1.5">
                {group.shortcuts.map((sc) => (
                  <div
                    key={sc.key}
                    className="flex items-center justify-between text-xs py-1 px-1.5 hover:bg-slate-50"
                  >
                    <span className="text-slate-700 font-sans text-xs">{sc.description}</span>
                    <kbd className="px-2 py-0.5 bg-slate-100 border border-slate-300 font-mono text-[11px] font-bold text-slate-800 shadow-2xs rounded-none">
                      {sc.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer Note */}
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] font-mono text-slate-500">
          <span>Press <kbd className="px-1 bg-white border border-slate-300 text-[10px]">Esc</kbd> to exit</span>
          <span className="text-slate-400">FEIOS v2.4 Institutional Ergonomics</span>
        </div>
      </div>
    </div>
  );
}
