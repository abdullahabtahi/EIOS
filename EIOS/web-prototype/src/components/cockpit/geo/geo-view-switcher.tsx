'use client';

import * as React from 'react';
import { VIEWS, type ViewId } from './geo-views';

export const VIEW_PANEL_ID = 'geo-view-panel';
export const viewTabId = (id: ViewId): string => `geo-view-${id}`;

/** The three questions the map can answer; one is open at a time. Arrow keys move between them, like the persona strip. */
export function GeoViewSwitcher({ current, onChange }: { readonly current: ViewId; readonly onChange: (id: ViewId) => void }) {
  const move = (to: number) => {
    const next = VIEWS[(to + VIEWS.length) % VIEWS.length];
    onChange(next.id);
    document.getElementById(viewTabId(next.id))?.focus();
  };
  return (
    <div role="tablist" aria-label="Map view" className="inline-flex gap-0.5 border border-cx-line bg-cx-sub-2 p-0.5 shadow-md">
      {VIEWS.map((view, index) => {
        const active = view.id === current;
        return (
          <button
            key={view.id}
            id={viewTabId(view.id)}
            role="tab"
            type="button"
            aria-selected={active}
            aria-controls={VIEW_PANEL_ID}
            tabIndex={active ? 0 : -1}
            title={view.question}
            onClick={() => onChange(view.id)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowRight') move(index + 1);
              else if (e.key === 'ArrowLeft') move(index - 1);
              else if (e.key === 'Home') move(0);
              else if (e.key === 'End') move(VIEWS.length - 1);
              else return;
              e.preventDefault();
            }}
            className={`cursor-pointer whitespace-nowrap px-3 py-1.5 text-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
              active ? 'border border-cx-line bg-white font-semibold text-cx-accent shadow-xs' : 'border border-transparent text-cx-ink-soft hover:text-cx-ink'
            }`}>
            {view.label}
          </button>
        );
      })}
    </div>
  );
}
