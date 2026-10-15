'use client';

import * as React from 'react';
import type { Lead } from './geo-leads';
import type { GeoSelection } from './geo-types';

/** Rows shown before "Show all"; the map is capped on the same ranking, so the top rows are the arcs you see. */
export const COLLAPSED_LEADS = 8;
const DOT = { high: 'bg-cx-bad', medium: 'bg-cx-warn-solid' } as const;
const same = (a: GeoSelection, b: NonNullable<GeoSelection>): boolean => a?.kind === b.kind && a.id === b.id;

function Row({ lead, selected, onSelect }: { readonly lead: Lead; readonly selected: boolean; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  return (
    <li>
      <button
        type="button"
        aria-pressed={selected}
        onClick={() => onSelect(lead.selection)}
        className={`flex w-full cursor-pointer items-start gap-2.5 px-2 py-1.5 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent ${
          selected ? 'bg-cx-select' : 'hover:bg-cx-sub-2'
        }`}>
        <span aria-hidden="true" className={`mt-1.5 size-2 shrink-0 ${lead.tier ? DOT[lead.tier] : ''}`} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-medium text-cx-ink">{lead.title}</span>
          <span className="block truncate text-label text-cx-muted">
            {lead.tier && <span className="font-semibold text-cx-ink-soft">{lead.tier === 'high' ? 'High' : 'Medium'} · </span>}
            {lead.detail}
          </span>
        </span>
      </button>
    </li>
  );
}

/** The ranked starting points for the open view. Clicking a row picks it and the map moves to it. */
export function GeoLeadList({ leads, selected, onSelect }: { readonly leads: readonly Lead[]; readonly selected: GeoSelection; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  const [all, setAll] = React.useState(false);
  const shown = all ? leads : leads.slice(0, COLLAPSED_LEADS);
  const groups = [...new Set(shown.map((l) => l.group ?? ''))];
  if (leads.length === 0) return <p className="text-xs text-cx-muted">Nothing to list for this view.</p>;
  return (
    <div className="space-y-2">
      {groups.map((group) => (
        <div key={group}>
          {group && <h4 className="px-2 pb-1 pt-2 text-label font-semibold text-cx-muted">{group}</h4>}
          <ul className="-mx-2 divide-y divide-cx-line-soft">
            {shown
              .filter((l) => (l.group ?? '') === group)
              .map((lead) => (
                <Row key={lead.key} lead={lead} selected={same(selected, lead.selection)} onSelect={onSelect} />
              ))}
          </ul>
        </div>
      ))}
      {leads.length > COLLAPSED_LEADS && (
        <button
          type="button"
          aria-expanded={all}
          onClick={() => setAll((v) => !v)}
          className="cursor-pointer text-xs font-semibold text-cx-accent outline-none hover:text-cx-accent-strong focus-visible:ring-2 focus-visible:ring-cx-accent">
          {all ? 'Show fewer' : `Show all ${leads.length}`}
        </button>
      )}
    </div>
  );
}
