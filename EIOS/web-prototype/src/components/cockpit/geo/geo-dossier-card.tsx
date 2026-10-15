'use client';

import * as React from 'react';
import Link from 'next/link';
import { Icon } from '@/components/ui/icon';
import { GeoAccountFacts, mapHref, useGeoAccount } from './geo-account';

const ACCOUNT_ID = /^[A-Z]{2}[0-9]{3,8}$/;

/**
 * The geography of the account under investigation, inside its dossier: where it registered, where it logs in from,
 * any shared exit or impossible jump, and its links in the graph, with a way onto the map. Absent when the backend has
 * no geography for it (an outage says so; an unknown account shows nothing).
 */
export function GeoDossierCard({ entityId }: { readonly entityId: string }) {
  const valid = ACCOUNT_ID.test(entityId);
  const state = useGeoAccount(valid ? entityId : null);
  if (!valid || !state || (state.status === 'error' && state.httpStatus === 404)) return null;
  const flagged =
    state.status === 'ready' && (state.data.lenses.shared_exit.flag || state.data.lenses.travel.flag || state.data.lenses.mismatch.flag);
  return (
    <section aria-label="Geography" className="space-y-2.5 border border-slate-200 bg-slate-50/50 p-3.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-title font-sans font-semibold text-slate-900">
          Geography
          {flagged && <span className="border border-cx-bad-line bg-cx-bad-bg px-1 py-0.5 font-mono text-label font-bold text-cx-bad">FLAGGED</span>}
        </h3>
        <Link
          href={mapHref(entityId)}
          className="inline-flex items-center gap-1 text-label font-semibold text-cx-accent outline-none hover:text-cx-accent-strong focus-visible:ring-2 focus-visible:ring-cx-accent">
          Open in map
          <Icon icon="arrow_forward" size="sm" />
        </Link>
      </div>
      {state.status === 'ready' ? (
        <GeoAccountFacts account={state.data} />
      ) : state.status === 'loading' ? (
        <div role="status" aria-label="Loading geography" className="h-16 animate-pulse bg-cx-sub-2 motion-reduce:animate-none" />
      ) : (
        <p role="alert" className="text-xs text-cx-warn">
          Geography could not be loaded{state.httpStatus ? ` (HTTP ${state.httpStatus})` : ''}. Nothing from it is shown.
        </p>
      )}
    </section>
  );
}
