'use client';

/**
 * What the latest change of a published list does to this book, for the MLRO: one row per country the change names, the
 * most exposed first, and behind each row what the book does there (accounts registered, logging in, paying through
 * it, shared exits located there, accounts one link away in the graph). Leaving a list ends a duty to apply enhanced
 * measures; it does not end the activity.
 */

import * as React from 'react';
import { formatUsd } from './geo-format';
import { GeoStatus } from './geo-status';
import type { GeoListChange, GeoSelection, ListChangeCountry } from './geo-types';
import type { ResourceState } from './use-geo-resource';

const COUNT = new Intl.NumberFormat('en-US');
const LISTING: Readonly<Record<string, string>> = {
  call_for_action: 'call for action',
  increased_monitoring: 'increased monitoring',
  eu_high_risk: 'EU high-risk',
};
const listingText = (listing: string | null): string => (listing ? (LISTING[listing] ?? listing) : 'not listed');
const NO_SHARE = '—';

interface ChangeRow {
  readonly country: ListChangeCountry;
  readonly what: string;
  readonly share: number | null;
}

function rowsOf(data: GeoListChange): readonly ChangeRow[] {
  const share = (iso2: string, shares: Readonly<Record<string, number>> | null) => shares?.[iso2] ?? null;
  return [
    ...data.added.countries.map((country) => ({ country, what: `Added · ${listingText(country.after)}`, share: share(country.iso2, data.added.session_shares) })),
    ...data.removed.countries.map((country) => ({ country, what: `Removed · was ${listingText(country.before)}`, share: share(country.iso2, data.removed.session_shares) })),
    ...data.relisted.countries.map((country) => ({
      country,
      what: `Moved · ${listingText(country.before)} → ${listingText(country.after)}`,
      share: share(country.iso2, data.relisted.session_shares),
    })),
  ].sort((a, b) => b.country.exposed_accounts - a.country.exposed_accounts || a.country.name.localeCompare(b.country.name));
}

function facts(c: ListChangeCountry): string[] {
  const out = [
    c.registered_accounts > 0 ? `${COUNT.format(c.registered_accounts)} registered there` : null,
    c.login_accounts ? `${COUNT.format(c.login_accounts)} log in from it` : null,
    c.payment_accounts > 0 ? `${COUNT.format(c.payment_accounts)} pay through it (${formatUsd(c.payment_volume_usd)})` : null,
    c.linked_accounts ? `${COUNT.format(c.linked_accounts)} one link away` : null,
  ];
  return out.filter((f): f is string => f !== null);
}

function Facts({ c }: { readonly c: ListChangeCountry }) {
  const listed = facts(c);
  return (
    <div className="mt-1 space-y-0.5 pb-1 text-label text-cx-ink-soft">
      <p>{listed.length > 0 ? listed.join(' · ') : 'No account of this book touches it'}</p>
      {c.shared_exits && c.shared_exits.length > 0 && <p className="font-mono text-cx-bad">Shared exit here: {c.shared_exits.join(', ')}</p>}
      {c.linked_accounts === null && c.exposed_accounts > 0 && <p className="text-cx-muted">Links not available: the graph could not be reached</p>}
    </div>
  );
}

function Row({ row, open, onToggle }: { readonly row: ChangeRow; readonly open: boolean; readonly onToggle: () => void }) {
  const { country: c } = row;
  return (
    <tr className="border-t border-cx-line-soft align-top">
      <td className="py-1.5 pr-2">
        <button
          type="button"
          aria-expanded={open}
          onClick={onToggle}
          className="block w-full cursor-pointer text-left outline-none focus-visible:ring-2 focus-visible:ring-cx-accent">
          <span className="block text-xs font-medium text-cx-ink">{c.name}</span>
          <span className="block text-label text-cx-muted">{row.what}</span>
        </button>
        {open && <Facts c={c} />}
      </td>
      <td className={`py-1.5 pr-2 text-right font-mono text-xs tabular-nums ${c.exposed_accounts === 0 ? 'text-cx-faint' : 'text-cx-ink'}`}>{COUNT.format(c.exposed_accounts)}</td>
      <td className={`py-1.5 text-right font-mono text-xs tabular-nums ${row.share ? 'text-cx-ink' : 'text-cx-faint'}`}>{row.share === null ? NO_SHARE : `${row.share.toFixed(1)}%`}</td>
    </tr>
  );
}

function Body({ data, onSelect }: { readonly data: GeoListChange; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  const [open, setOpen] = React.useState<string | null>(null);
  const rows = rowsOf(data);
  const graph = data.graph.error
    ? `Links unavailable: ${data.graph.error}`
    : data.graph.source
      ? `Links from ${data.graph.source.startsWith('graph.bigquery') ? 'BigQuery Graph' : 'the local graph double'}${data.graph.seconds !== null ? ` in ${data.graph.seconds.toFixed(1)} s` : ''}`
      : null;
  return (
    <div className="space-y-2">
      <p className="text-label text-cx-muted">Compared with {data.before.label}.</p>
      <table className="w-full">
        <thead>
          <tr className="text-label text-cx-muted">
            <th scope="col" className="pb-1 pr-2 text-left font-normal">Country</th>
            <th scope="col" className="pb-1 pr-2 text-right font-normal">Accounts</th>
            <th scope="col" className="pb-1 text-right font-normal">Sessions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <Row
              key={r.country.iso2}
              row={r}
              open={open === r.country.iso2}
              onToggle={() => {
                setOpen((now) => (now === r.country.iso2 ? null : r.country.iso2));
                if (open !== r.country.iso2) onSelect({ kind: 'country', id: r.country.iso2 });
              }}
            />
          ))}
        </tbody>
      </table>
      {data.removed.countries.length > 0 && (
        <p className="text-label text-cx-muted">Leaving a list ends the duty to apply enhanced measures; the activity continues.</p>
      )}
      <details className="text-label text-cx-muted">
        <summary className="cursor-pointer outline-none hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent">Sources and method</summary>
        <p className="mt-1">
          {graph}
          {graph ? ' · ' : ''}Sources: {data.after.source}; earlier edition: {data.before.source}.
        </p>
      </details>
    </div>
  );
}

export interface GeoListChangeProps {
  readonly state: ResourceState<GeoListChange> | null;
  readonly onClose: () => void;
  readonly onSelect: (selection: NonNullable<GeoSelection>) => void;
}

export function GeoListChangePanel({ state, onClose, onSelect }: GeoListChangeProps) {
  return (
    <section aria-label="What changed on the lists" className="space-y-2 border-y border-cx-line py-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-title font-sans font-semibold text-cx-ink">
          {state?.status === 'ready' ? state.data.after.label : 'What changed on the list'}
        </h3>
        <button type="button" onClick={onClose} className="cursor-pointer text-label text-cx-muted underline outline-none hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent">
          Close
        </button>
      </div>
      {state === null || state.status !== 'ready' ? state && <GeoStatus label="list change" state={state} /> : <Body data={state.data} onSelect={onSelect} />}
    </section>
  );
}
