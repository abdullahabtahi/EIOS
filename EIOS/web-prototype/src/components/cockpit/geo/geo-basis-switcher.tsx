'use client';

import * as React from 'react';
import { BASES, type BasisId } from './geo-basis';

/** Which published list colours the map. The lists differ, so showing one at a time keeps each one's claim its own. */
export function GeoBasisSwitcher({ current, onChange }: { readonly current: BasisId; readonly onChange: (id: BasisId) => void }) {
  return (
    <div role="group" aria-label="Risk basis" className="space-y-1">
      <p className="text-label font-semibold text-cx-muted">Colour countries by</p>
      <div className="inline-flex gap-0.5 border border-cx-line bg-cx-sub-2 p-0.5">
        {BASES.map((b) => {
          const active = b.id === current;
          return (
            <button
              key={b.id}
              type="button"
              aria-pressed={active}
              title={b.title}
              onClick={() => onChange(b.id)}
              className={`cursor-pointer whitespace-nowrap px-2.5 py-1 text-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
                active ? 'border border-cx-line bg-white font-semibold text-cx-accent shadow-xs' : 'border border-transparent text-cx-ink-soft hover:text-cx-ink'
              }`}>
              {b.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
