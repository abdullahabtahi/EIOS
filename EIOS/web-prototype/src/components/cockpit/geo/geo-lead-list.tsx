'use client';

import * as React from 'react';
import type { Lead } from './geo-leads';
import type { GeoSelection } from './geo-types';

/** Rows shown before "Show all"; the map is capped on the same ranking, so the top rows are the arcs you see. */
export const COLLAPSED_LEADS = 8;
const DOT = { high: 'bg-cx-bad', medium: 'bg-cx-warn-solid' } as const;
const same = (a: GeoSelection, b: NonNullable<GeoSelection>): boolean => a?.kind === b.kind && a.id === b.id;
const ROW = '[data-lead-row]';

function Row({ lead, selected, onSelect }: { readonly lead: Lead; readonly selected: boolean; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  return (
    <li>
      <button
        type="button"
        data-lead-row=""
        aria-pressed={selected}
        onClick={() => onSelect(lead.selection)}
        className={`flex w-full cursor-pointer items-start gap-2.5 px-2 py-1.5 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent ${
          selected ? 'bg-cx-select' : 'hover:bg-cx-sub-2'
        }`}>
        <span aria-hidden="true" className={`mt-1.5 size-2 shrink-0 ${lead.tier ? DOT[lead.tier] : ''}`} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-medium text-cx-ink">{lead.title}</span>
          <span className="block truncate font-mono text-label tabular-nums text-cx-muted">{lead.detail}</span>
          {lead.share !== undefined && (
            <span aria-hidden="true" className="mt-1 block h-0.5 bg-cx-line-soft">
              <span data-testid="lead-bar" aria-hidden="true" className="block h-full bg-cx-faint" style={{ width: `${Math.round(lead.share * 100)}%` }} />
            </span>
          )}
        </span>
      </button>
    </li>
  );
}

/** Moves focus between the rows: arrows or j and k, Home and End. Enter and Space are the buttons' own. */
function moveFocus(e: React.KeyboardEvent<HTMLElement>): void {
  const rows = [...e.currentTarget.querySelectorAll<HTMLElement>(ROW)];
  const at = rows.indexOf(document.activeElement as HTMLElement);
  if (at < 0) return;
  const next =
    e.key === 'ArrowDown' || e.key === 'j' ? Math.min(at + 1, rows.length - 1)
    : e.key === 'ArrowUp' || e.key === 'k' ? Math.max(at - 1, 0)
    : e.key === 'Home' ? 0
    : e.key === 'End' ? rows.length - 1
    : -1;
  if (next < 0) return;
  e.preventDefault();
  rows[next].focus();
}

const matches = (lead: Lead, text: string): boolean => `${lead.title} ${lead.detail}`.toLowerCase().includes(text.trim().toLowerCase());

/** The ranked starting points for the open view. Clicking a row picks it and the map moves to it. */
export function GeoLeadList({ leads, selected, onSelect }: { readonly leads: readonly Lead[]; readonly selected: GeoSelection; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  const [all, setAll] = React.useState(false);
  const [filter, setFilter] = React.useState('');
  const filtering = filter.trim() !== '';
  const found = filtering ? leads.filter((l) => matches(l, filter)) : leads;
  const shown = all || filtering ? found : found.slice(0, COLLAPSED_LEADS);
  const groups = [...new Set(shown.map((l) => l.group ?? ''))];
  if (leads.length === 0) return <p className="text-xs text-cx-muted">Nothing to list for this view.</p>;
  return (
    <div className="space-y-2" onKeyDown={moveFocus}>
      {leads.length > COLLAPSED_LEADS && (
        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== 'Escape') return;
            e.stopPropagation();
            setFilter('');
          }}
          placeholder="Filter by country"
          aria-label="Filter the list"
          className="w-full rounded-none border border-cx-line bg-white px-2 py-1.5 text-xs text-cx-ink outline-none placeholder:text-cx-muted focus-visible:ring-2 focus-visible:ring-cx-accent"
        />
      )}
      {found.length === 0 && <p className="text-xs text-cx-muted">Nothing matches “{filter.trim()}”.</p>}
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
      {!filtering && leads.length > COLLAPSED_LEADS && (
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
