'use client';

/**
 * What the latest change of a published list does to this book, for the MLRO: countries added and removed, and for each
 * the accounts registered there, logging in from it, paying through it, the shared exits located there and the accounts
 * one link away in the graph. Leaving a list ends a duty to apply enhanced measures; it does not end the activity.
 */

import * as React from 'react';
import { formatUsd } from './geo-format';
import { GeoStatus } from './geo-status';
import type { GeoListChange, GeoSelection, ListChangeCountry, ListChangeGroup, ListId } from './geo-types';
import type { ResourceState } from './use-geo-resource';

const LISTS: readonly { readonly id: ListId; readonly label: string }[] = [
  { id: 'fatf', label: 'FATF, June 2026 plenary' },
  { id: 'eu', label: 'EU, January 2026 amendments' },
];
const COUNT = new Intl.NumberFormat('en-US');
const LISTING: Readonly<Record<string, string>> = {
  call_for_action: 'call for action',
  increased_monitoring: 'increased monitoring',
  eu_high_risk: 'EU high-risk',
};

const listingText = (listing: string | null): string => (listing ? (LISTING[listing] ?? listing) : 'not listed');

function facts(c: ListChangeCountry): string[] {
  const out = [
    c.registered_accounts > 0 ? `${COUNT.format(c.registered_accounts)} registered there` : null,
    c.login_accounts ? `${COUNT.format(c.login_accounts)} log in from it` : null,
    c.payment_accounts > 0 ? `${COUNT.format(c.payment_accounts)} pay through it (${formatUsd(c.payment_volume_usd)})` : null,
    c.linked_accounts ? `${COUNT.format(c.linked_accounts)} one link away` : null,
  ];
  return out.filter((f): f is string => f !== null);
}

function CountryRow({ c, share, onSelect }: { readonly c: ListChangeCountry; readonly share: number | null; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  const listed = facts(c);
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect({ kind: 'country', id: c.iso2 })}
        className="w-full cursor-pointer space-y-0.5 border border-cx-line bg-white px-2.5 py-2 text-left hover:border-cx-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cx-accent"
      >
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-xs font-semibold text-cx-ink">
            {c.name} <span className="font-mono text-cx-muted">{c.iso2}</span>
          </span>
          {share !== null && <span className="font-mono text-label text-cx-muted">{share.toFixed(1)}% of sessions</span>}
        </div>
        <div className="text-label text-cx-muted">
          {listingText(c.before)} → {listingText(c.after)}
        </div>
        <div className="text-label text-cx-ink-soft">
          {listed.length > 0 ? listed.join(' · ') : 'No account of this book touches it'}
        </div>
        {c.shared_exits && c.shared_exits.length > 0 && (
          <div className="font-mono text-label text-cx-bad">Shared exit here: {c.shared_exits.join(', ')}</div>
        )}
        {c.linked_accounts === null && c.exposed_accounts > 0 && (
          <div className="text-label text-cx-muted">Links not available: the graph could not be reached</div>
        )}
      </button>
    </li>
  );
}

function Group({ title, note, group, onSelect }: { readonly title: string; readonly note?: string; readonly group: ListChangeGroup; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  if (group.countries.length === 0) return null;
  return (
    <section className="space-y-1.5" aria-label={title}>
      <h4 className="text-xs font-semibold text-cx-ink">
        {title} · {COUNT.format(group.exposed_accounts)} accounts touched
      </h4>
      {note && <p className="text-label text-cx-muted">{note}</p>}
      <ul className="space-y-1.5">
        {group.countries.map((c) => (
          <CountryRow key={c.iso2} c={c} share={group.session_shares?.[c.iso2] ?? null} onSelect={onSelect} />
        ))}
      </ul>
    </section>
  );
}

function Body({ data, onSelect }: { readonly data: GeoListChange; readonly onSelect: (s: NonNullable<GeoSelection>) => void }) {
  const graph = data.graph.error
    ? `Links unavailable: ${data.graph.error}`
    : data.graph.source
      ? `Links from ${data.graph.source.startsWith('graph.bigquery') ? 'BigQuery Graph' : 'the local graph double'}${data.graph.seconds !== null ? ` in ${data.graph.seconds.toFixed(1)} s` : ''}`
      : null;
  return (
    <div className="space-y-3">
      <p className="text-label text-cx-muted">
        {data.before.label} ({data.before.in_force}) → {data.after.label} ({data.after.in_force})
      </p>
      <Group title="Added to the list" group={data.added} onSelect={onSelect} />
      <Group
        title="Removed from the list"
        note="Leaving a list ends the duty to apply enhanced measures; the activity below continues."
        group={data.removed}
        onSelect={onSelect}
      />
      <Group title="Moved between lists" group={data.relisted} onSelect={onSelect} />
      <p className="text-label text-cx-muted">
        {graph}
        {graph ? ' · ' : ''}Sources: {data.after.source}; earlier edition: {data.before.source}.
      </p>
    </div>
  );
}

export interface GeoListChangeProps {
  readonly listId: ListId;
  readonly state: ResourceState<GeoListChange> | null;
  readonly onList: (id: ListId) => void;
  readonly onClose: () => void;
  readonly onSelect: (selection: NonNullable<GeoSelection>) => void;
}

export function GeoListChangePanel({ listId, state, onList, onClose, onSelect }: GeoListChangeProps) {
  return (
    <section aria-label="What changed on the lists" className="space-y-2 border border-cx-line bg-cx-sub p-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-title font-sans font-semibold text-cx-ink">What the latest list change does to us</h3>
        <button type="button" onClick={onClose} className="cursor-pointer text-label text-cx-muted underline hover:text-cx-ink">
          Close
        </button>
      </div>
      <div role="radiogroup" aria-label="Which list" className="flex gap-1">
        {LISTS.map((l) => (
          <button
            key={l.id}
            type="button"
            role="radio"
            aria-checked={l.id === listId}
            onClick={() => onList(l.id)}
            className={`cursor-pointer border px-2 py-1 text-label ${l.id === listId ? 'border-cx-line bg-white text-cx-ink' : 'border-transparent text-cx-muted hover:text-cx-ink'}`}
          >
            {l.label}
          </button>
        ))}
      </div>
      {state === null || state.status !== 'ready' ? (
        state && <GeoStatus label="list change" state={state} />
      ) : (
        <Body data={state.data} onSelect={onSelect} />
      )}
    </section>
  );
}
