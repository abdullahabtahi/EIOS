import * as React from 'react';
import type { ListId } from './geo-types';

const LISTS: readonly { readonly id: ListId; readonly label: string }[] = [
  { id: 'fatf', label: 'FATF' },
  { id: 'eu', label: 'EU' },
];

/** The two ways to read the Jurisdictions view: where the lists stand today, or what their latest change did to this book. */
export function GeoModeSwitch({ changing, total, onMode }: { readonly changing: boolean; readonly total: number | null; readonly onMode: (changing: boolean) => void }) {
  const item = (on: boolean, label: React.ReactNode, changingTo: boolean) => (
    <button
      type="button"
      aria-pressed={on}
      onClick={() => onMode(changingTo)}
      className={`flex flex-1 cursor-pointer items-center justify-center gap-1.5 border px-3 py-1.5 text-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
        on ? 'border-cx-line bg-white font-semibold text-cx-accent' : 'border-transparent text-cx-ink-soft hover:text-cx-ink'
      }`}>
      {label}
    </button>
  );
  return (
    <div role="group" aria-label="What to read" className="flex gap-0.5 border border-cx-line bg-cx-sub-2 p-0.5">
      {item(!changing, 'Where we stand', false)}
      {item(
        changing,
        <>
          What changed
          {total !== null && total > 0 && <span className="font-mono text-label tabular-nums text-cx-muted">{total}</span>}
        </>,
        true,
      )}
    </div>
  );
}

/** Which list's change is read while in that mode, each with the number of countries it moved. */
export function GeoChangeLists({ list, counts, onList }: { readonly list: ListId; readonly counts: Readonly<Partial<Record<ListId, number>>>; readonly onList: (id: ListId) => void }) {
  return (
    <div role="group" aria-label="Which list" className="inline-flex gap-0.5 border border-cx-line bg-cx-sub-2 p-0.5">
      {LISTS.map((l) => {
        const on = l.id === list;
        const n = counts[l.id];
        return (
          <button
            key={l.id}
            type="button"
            aria-pressed={on}
            onClick={() => onList(l.id)}
            className={`flex cursor-pointer items-center gap-1.5 border px-2.5 py-1 text-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
              on ? 'border-cx-line bg-white font-semibold text-cx-accent' : 'border-transparent text-cx-ink-soft hover:text-cx-ink'
            }`}>
            {l.label}
            {n !== undefined && <span className="font-mono text-label tabular-nums text-cx-muted">{n}</span>}
          </button>
        );
      })}
    </div>
  );
}
