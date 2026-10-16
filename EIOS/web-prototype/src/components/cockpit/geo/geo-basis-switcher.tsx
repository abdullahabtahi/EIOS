'use client';

import * as React from 'react';
import { BASES, type BasisId } from './geo-basis';
import type { ListId } from './geo-types';

export interface GeoBasisSwitcherProps {
  readonly current: BasisId;
  readonly onChange: (id: BasisId) => void;
  /** How many countries each list's latest change names, for the lists that have one loaded. */
  readonly changes?: Readonly<Partial<Record<ListId, number>>>;
  /** The list whose change is open, if any. */
  readonly comparing?: ListId | null;
  readonly onCompare?: (id: ListId) => void;
}

const hasChange = (id: BasisId): id is ListId => id === 'fatf' || id === 'eu';

/**
 * Which published list colours the map. The lists differ, so showing one at a time keeps each one's claim its own. A list
 * whose latest change is known carries the number of countries it moved; the number opens the comparison.
 */
export function GeoBasisSwitcher({ current, onChange, changes = {}, comparing = null, onCompare }: GeoBasisSwitcherProps) {
  return (
    <div role="group" aria-label="Risk basis" className="space-y-1">
      <p className="text-label font-semibold text-cx-muted">Colour countries by</p>
      <div className="inline-flex gap-0.5 border border-cx-line bg-cx-sub-2 p-0.5">
        {BASES.map((b) => {
          const active = b.id === current;
          const changed = hasChange(b.id) ? changes[b.id] : undefined;
          return (
            <div key={b.id} className={`flex items-stretch border ${active ? 'border-cx-line bg-white' : 'border-transparent'}`}>
              <button
                type="button"
                aria-pressed={active}
                title={b.title}
                onClick={() => onChange(b.id)}
                className={`cursor-pointer whitespace-nowrap px-2.5 py-1 text-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
                  active ? 'font-semibold text-cx-accent' : 'text-cx-ink-soft hover:text-cx-ink'
                }`}>
                {b.label}
              </button>
              {changed !== undefined && changed > 0 && hasChange(b.id) && onCompare && (
                <button
                  type="button"
                  aria-pressed={comparing === b.id}
                  aria-label={`Compare ${b.label} before and after its latest change: ${changed} ${changed === 1 ? 'country' : 'countries'} changed`}
                  title={`${changed} ${changed === 1 ? 'country' : 'countries'} changed in the latest edition. Compare.`}
                  onClick={() => onCompare(b.id as ListId)}
                  className={`my-0.5 mr-1 cursor-pointer px-1.5 font-mono text-label tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-cx-accent ${
                    comparing === b.id ? 'bg-cx-accent text-white' : 'bg-cx-select text-cx-accent hover:bg-cx-sub-2'
                  }`}>
                  {changed}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
