'use client';

import * as React from 'react';
import Link from 'next/link';
import { Icon } from '@/components/ui/icon';
import { GeoAccountFacts, workstationHref } from './geo-account';
import { GeoStatus } from './geo-status';
import type { GeoAccount } from './geo-types';
import type { ResourceState } from './use-geo-resource';

export interface GeoAccountDetailProps {
  readonly accountId: string;
  readonly state: ResourceState<GeoAccount>;
  readonly onClear: () => void;
  readonly onPickAccount: (id: string) => void;
}

/** A picked account in the map's panel: its geography, its links in the graph, and the way into its case. */
export function GeoAccountDetail({ accountId, state, onClear, onPickAccount }: GeoAccountDetailProps) {
  return (
    <section aria-label="Selection" className="border border-cx-line bg-cx-sub p-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-mono text-title font-semibold leading-snug text-cx-ink">{accountId}</h3>
        <button
          type="button"
          aria-label="Clear selection"
          title="Clear selection (Esc)"
          onClick={onClear}
          className="-m-1 flex size-6 shrink-0 cursor-pointer items-center justify-center text-cx-muted outline-none hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent">
          <Icon icon="close" size="sm" />
        </button>
      </div>
      <div className="mt-2">
        {state.status === 'ready' ? (
          <GeoAccountFacts account={state.data} onPickAccount={onPickAccount} />
        ) : state.status === 'error' && state.httpStatus === 404 ? (
          <p className="text-xs text-cx-muted">No account {accountId} in this world.</p>
        ) : (
          <GeoStatus label="account's geography" state={state} />
        )}
      </div>
      <Link
        href={workstationHref(accountId)}
        className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-cx-accent outline-none hover:text-cx-accent-strong focus-visible:ring-2 focus-visible:ring-cx-accent">
        Open the case in the AML workstation
        <Icon icon="arrow_forward" size="sm" />
      </Link>
    </section>
  );
}
