'use client';

/**
 * The right-hand column: Explore (the lists and the picked mark) or Ask (the assistant), behind one switch, like the
 * dossier column's Dossier and Chat. Both stay mounted so a pending answer and a half-typed question survive a switch.
 */

import * as React from 'react';

export type SidePanel = 'explore' | 'ask';

function Tab({ active, onClick, children }: { readonly active: boolean; readonly onClick: () => void; readonly children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`relative cursor-pointer px-3 py-1 text-xs font-medium transition-colors ${
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
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div role="tablist" aria-label="Explore or ask" className="flex shrink-0 items-center gap-1 border-b border-cx-line bg-cx-sub px-2 py-1.5">
        <Tab active={panel === 'explore'} onClick={() => onPanel('explore')}>
          Explore
        </Tab>
        <Tab active={panel === 'ask'} onClick={() => onPanel('ask')}>
          Ask
        </Tab>
      </div>
      <div className={`min-h-0 flex-1 ${panel === 'explore' ? 'flex flex-col' : 'hidden'}`}>{explore}</div>
      <div className={`min-h-0 flex-1 ${panel === 'ask' ? 'flex flex-col' : 'hidden'}`}>{ask}</div>
    </div>
  );
}
