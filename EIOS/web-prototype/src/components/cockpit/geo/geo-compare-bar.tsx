import * as React from 'react';

export type CompareSide = 'before' | 'after';

/** On the map while a comparison is open: which edition of the list the colours show, so the change is seen to happen. */
export function GeoCompareBar({ side, onSide, label }: { readonly side: CompareSide; readonly onSide: (s: CompareSide) => void; readonly label: string }) {
  return (
    <div role="group" aria-label="Edition shown on the map" className="flex items-center gap-2 border border-cx-line bg-white p-1 pr-3">
      <div className="inline-flex gap-0.5 bg-cx-sub-2 p-0.5">
        {(['before', 'after'] as const).map((s) => (
          <button
            key={s}
            type="button"
            aria-pressed={side === s}
            onClick={() => onSide(s)}
            className={`cursor-pointer px-2.5 py-1 text-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-cx-accent ${
              side === s ? 'border border-cx-line bg-white font-semibold text-cx-accent' : 'border border-transparent text-cx-ink-soft hover:text-cx-ink'
            }`}>
            {s === 'before' ? 'Before' : 'After'}
          </button>
        ))}
      </div>
      <span className="text-label text-cx-muted">{label}</span>
    </div>
  );
}
