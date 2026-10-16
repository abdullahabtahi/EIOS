'use client';

/**
 * The right-hand column: Explore (the lists and the picked mark) or Ask (the assistant), behind one switch, like the
 * dossier column's Dossier and Chat. Both stay mounted so a pending answer and a half-typed question survive a switch.
 */

import * as React from 'react';

export type SidePanel = 'explore' | 'ask';

const TAB_ID = { explore: 'geo-side-tab-explore', ask: 'geo-side-tab-ask' } as const;
const PANEL_ID = { explore: 'geo-side-panel-explore', ask: 'geo-side-panel-ask' } as const;
const ORDER: readonly SidePanel[] = ['explore', 'ask'];

function Tab({ id, active, onClick, children }: { readonly id: SidePanel; readonly active: boolean; readonly onClick: () => void; readonly children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      id={TAB_ID[id]}
      aria-selected={active}
      aria-controls={PANEL_ID[id]}
      tabIndex={active ? 0 : -1}
      onClick={onClick}
      className={`relative cursor-pointer px-3 py-1 text-xs font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
        active ? 'border border-cx-line bg-white text-cx-ink' : 'border border-transparent text-cx-muted hover:text-cx-ink'
      }`}
    >
      {children}
    </button>
  );
}

export interface GeoSideProps {
  readonly panel: SidePanel;
  readonly onPanel: (panel: SidePanel) => void;
  readonly explore: React.ReactNode;
  readonly ask: React.ReactNode;
}

export function GeoSide({ panel, onPanel, explore, ask }: GeoSideProps) {
  // Arrow keys, Home and End move between the two tabs, and focus follows, as the tab pattern asks.
  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const at = ORDER.indexOf(panel);
    const next =
      e.key === 'ArrowRight' ? (at + 1) % ORDER.length
      : e.key === 'ArrowLeft' ? (at - 1 + ORDER.length) % ORDER.length
      : e.key === 'Home' ? 0
      : e.key === 'End' ? ORDER.length - 1
      : -1;
    if (next < 0) return;
    e.preventDefault();
    onPanel(ORDER[next]);
    document.getElementById(TAB_ID[ORDER[next]])?.focus();
  };
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div role="tablist" aria-label="Explore or ask" onKeyDown={onKeyDown} className="flex shrink-0 items-center gap-1 border-b border-cx-line bg-cx-sub px-2 py-1.5">
        <Tab id="explore" active={panel === 'explore'} onClick={() => onPanel('explore')}>
          Explore
        </Tab>
        <Tab id="ask" active={panel === 'ask'} onClick={() => onPanel('ask')}>
          Ask
        </Tab>
      </div>
      <div id={PANEL_ID.explore} aria-labelledby={TAB_ID.explore} className={`min-h-0 flex-1 ${panel === 'explore' ? 'flex flex-col' : 'hidden'}`}>{explore}</div>
      <div id={PANEL_ID.ask} aria-labelledby={TAB_ID.ask} className={`min-h-0 flex-1 ${panel === 'ask' ? 'flex flex-col' : 'hidden'}`}>{ask}</div>
    </div>
  );
}
