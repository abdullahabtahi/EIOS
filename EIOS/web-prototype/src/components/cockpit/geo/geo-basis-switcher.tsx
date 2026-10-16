'use client';

import * as React from 'react';
import { Icon } from '@/components/ui/icon';
import { BASES, type BasisId } from './geo-basis';

export interface GeoBasisSwitcherProps {
  readonly current: BasisId;
  readonly onChange: (id: BasisId) => void;
  /** How many countries the latest change of the list in view names; undefined when it has none (Basel) or is not read yet. */
  readonly changeCount?: number;
  /** Whether the comparison of that change is open. */
  readonly changing?: boolean;
  readonly onToggleChange?: () => void;
}

/**
 * Which published list colours the map. The lists differ, so showing one at a time keeps each one's claim its own. On
 * the same row, at the far right, an icon with the count opens what the latest change of that same list did to this book: one switcher, with
 * the change a reading of the list you are on.
 */
export function GeoBasisSwitcher({ current, onChange, changeCount, changing = false, onToggleChange }: GeoBasisSwitcherProps) {
  return (
    <div role="group" aria-label="Risk basis" className="space-y-1">
      <p className="text-label font-semibold text-cx-muted">Colour countries by</p>
      <div className="flex items-center justify-between gap-2">
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
        {changeCount !== undefined && changeCount > 0 && onToggleChange && (
          <button
            type="button"
            aria-pressed={changing}
            aria-label={`What changed in this list: ${changeCount} ${changeCount === 1 ? 'country' : 'countries'}`}
            title={`What changed: ${changeCount} ${changeCount === 1 ? 'country' : 'countries'} in the latest edition`}
            onClick={onToggleChange}
            className={`flex cursor-pointer items-center gap-1 border px-1.5 py-1 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
              changing ? 'border-cx-accent bg-cx-accent text-white' : 'border-cx-line bg-white text-cx-accent hover:border-cx-accent'
            }`}>
            <Icon icon="compare_arrows" size="sm" />
            <span className={`font-mono text-label tabular-nums ${changing ? 'text-white' : 'text-cx-muted'}`}>{changeCount}</span>
          </button>
        )}
      </div>
    </div>
  );
}
