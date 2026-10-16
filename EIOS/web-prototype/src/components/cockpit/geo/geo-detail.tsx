import * as React from 'react';
import { Icon } from '@/components/ui/icon';
import type { SelectionView } from './geo-format';

/** The picked mark in full: every fact the data holds for it, with a way to put it down. */
export interface GeoDetailProps {
  readonly view: SelectionView;
  readonly onClear: () => void;
  readonly onPickAccount?: (id: string) => void;
  /** Hand an account to the assistant for its SAR geography paragraph. */
  readonly onDraftSar?: (accountId: string) => void;
}

export function GeoDetail({ view, onClear, onPickAccount, onDraftSar }: GeoDetailProps) {
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
      {view.accounts && view.accounts.length > 0 && onPickAccount && (
        <div className="mt-2.5 space-y-1 border-t border-cx-line-soft pt-2">
          <p className="text-label font-semibold text-cx-ink-soft">Open an account</p>
          <ul className="flex flex-wrap gap-1">
            {view.accounts.map((id) => (
              <li key={id}>
                <button
                  type="button"
                  onClick={() => onPickAccount(id)}
                  className="cursor-pointer border border-cx-line bg-white px-1.5 py-0.5 font-mono text-label text-cx-accent outline-none hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-cx-accent">
                  {id}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {view.draftSarFor && onDraftSar && (
        <button
          type="button"
          aria-label={`Draft SAR paragraph for ${view.draftSarFor}`}
          onClick={() => onDraftSar(view.draftSarFor as string)}
          className="mt-2.5 flex w-full cursor-pointer items-center justify-between gap-2 bg-cx-ink px-3 py-2 text-left text-xs font-medium text-white outline-none hover:bg-black focus-visible:ring-2 focus-visible:ring-cx-accent focus-visible:ring-offset-1">
          <span>Draft SAR paragraph</span>
          <span className="font-mono text-label text-white/70">{view.draftSarFor}</span>
        </button>
      )}
      {view.note && <p className="mt-2 text-label text-cx-muted">{view.note}</p>}
    </section>
  );
}
