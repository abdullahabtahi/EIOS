import * as React from 'react';
import { Icon } from '@/components/ui/icon';
import type { SelectionView } from './geo-format';

/** The picked mark in full: every fact the data holds for it, with a way to put it down. */
export function GeoDetail({ view, onClear }: { readonly view: SelectionView; readonly onClear: () => void }) {
  return (
    <section aria-label="Selection" className="border border-cx-line bg-cx-sub p-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-title font-sans font-semibold leading-snug text-cx-ink">{view.title}</h3>
        <button
          type="button"
          aria-label="Clear selection"
          title="Clear selection (Esc)"
          onClick={onClear}
          className="-m-1 flex size-6 shrink-0 cursor-pointer items-center justify-center text-cx-muted outline-none hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent">
          <Icon icon="close" size="sm" />
        </button>
      </div>
      <dl className="mt-2 space-y-1 text-xs">
        {view.rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3">
            <dt className="text-cx-muted">{label}</dt>
            <dd className="text-right font-mono tabular-nums text-cx-ink">{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
