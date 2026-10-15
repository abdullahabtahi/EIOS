'use client';

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';
import { formatUsd, regionName } from './geo-format';
import type { GeoAccount } from './geo-types';
import type { ResourceState } from './use-geo-resource';

const COUNT = new Intl.NumberFormat('en-US');
const MAX_LINKED = 8;

/** One account's geography from the backend; null while no account is picked. Each account is fetched once per mount. */
export function useGeoAccount(accountId: string | null): ResourceState<GeoAccount> | null {
  const [state, setState] = React.useState<{ id: string; value: ResourceState<GeoAccount> } | null>(null);
  const [attempt, setAttempt] = React.useState(0);
  const reload = React.useCallback(() => setAttempt((n) => n + 1), []);

  React.useEffect(() => {
    if (!accountId) return;
    let live = true;
    authFetch(`/api/cockpit/geo/accounts/${encodeURIComponent(accountId)}`, { headers: { Accept: 'application/json' } })
      .then(async (res) => {
        if (!live) return;
        if (!res.ok) return setState({ id: accountId, value: { status: 'error', httpStatus: res.status, reload } });
        setState({ id: accountId, value: { status: 'ready', data: (await res.json()) as GeoAccount } });
      })
      .catch(() => live && setState({ id: accountId, value: { status: 'error', httpStatus: 0, reload } }));
    return () => {
      live = false;
    };
  }, [accountId, attempt, reload]);

  if (!accountId) return null;
  return state && state.id === accountId ? state.value : { status: 'loading' };
}

const plural = (n: number, one: string, many = `${one}s`) => `${COUNT.format(n)} ${n === 1 ? one : many}`;

/** The plain-language facts, each one a figure from the engine or the graph, never typed by a model. */
export function accountFacts(a: GeoAccount): readonly (readonly [label: string, value: string])[] {
  const abroad = a.login_countries.filter((c) => c.iso2 !== a.kyc_country);
  const exit = a.gateways.find((g) => g.gateway_id === a.lenses.shared_exit.gateway);
  const jumps = a.jumps;
  const money = a.payments.slice(0, 2).map((p) => `${regionName(p.iso2)} ${p.direction} ${formatUsd(p.volume_usd)}`);
  return [
    ['Registered in', regionName(a.kyc_country)],
    [
      'Logs in from',
      abroad.length === 0
        ? `home only (${plural(a.sessions, 'session')})`
        : abroad
            .slice(0, 3)
            .map((c) => `${regionName(c.iso2)} ${c.sessions} of ${a.sessions}`)
            .join(', '),
    ],
    [
      'Shared exit',
      exit ? `${exit.gateway_id}, used by ${plural(exit.accounts ?? 0, 'account')}` : a.sessions > 0 ? 'none' : 'not assessable',
    ],
    [
      'Impossible travel',
      jumps === null
        ? 'not assessable'
        : jumps.count === 0
          ? 'none'
          : `${plural(jumps.count, 'jump')}${jumps.examples[0] ? `, e.g. ${regionName(jumps.examples[0].from)} to ${regionName(jumps.examples[0].to)}, ${COUNT.format(jumps.examples[0].km)} km in ${jumps.examples[0].hours} h` : ''}`,
    ],
    ['Cross-border money', money.length ? money.join(', ') : 'none'],
  ];
}

export interface GeoAccountFactsProps {
  readonly account: GeoAccount;
  readonly onPickAccount?: (id: string) => void;
}

/** The account's facts and the accounts it is linked to in the graph, with the graph's source. */
export function GeoAccountFacts({ account, onPickAccount }: GeoAccountFactsProps) {
  const links = account.neighbourhood;
  const linked = [...new Map((links.rows ?? []).map((r) => [r.account_id, r])).values()];
  return (
    <div className="space-y-3">
      <dl className="space-y-1 text-xs">
        {accountFacts(account).map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3">
            <dt className="shrink-0 text-cx-muted">{label}</dt>
            <dd className="text-right text-cx-ink">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="space-y-1.5 border-t border-cx-line-soft pt-2">
        <p className="text-label font-semibold text-cx-ink-soft">
          Linked accounts{links.total != null ? ` (${COUNT.format(new Set((links.rows ?? []).map((r) => r.account_id)).size)})` : ''}
        </p>
        {links.error ? (
          <p className="text-label text-cx-warn">The graph could not answer: {links.error}</p>
        ) : linked.length === 0 ? (
          <p className="text-label text-cx-muted">No account shares a gateway or an identifier with this one (hubs excluded).</p>
        ) : (
          <ul className="flex flex-wrap gap-1">
            {linked.slice(0, MAX_LINKED).map((r) => (
              <li key={r.account_id}>
                {onPickAccount ? (
                  <button
                    type="button"
                    title={`Shares ${r.via === 'gateway' ? `gateway ${r.link}` : `a ${r.detail.toLowerCase().replace(/_/g, ' ')}`}; registered in ${regionName(r.kyc_country)}`}
                    onClick={() => onPickAccount(r.account_id)}
                    className="cursor-pointer border border-cx-line bg-white px-1.5 py-0.5 font-mono text-label text-cx-accent outline-none hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-cx-accent">
                    {r.account_id}
                  </button>
                ) : (
                  <span className="border border-cx-line px-1.5 py-0.5 font-mono text-label text-cx-ink-soft">{r.account_id}</span>
                )}
              </li>
            ))}
            {linked.length > MAX_LINKED && <li className="px-1 text-label text-cx-muted">+{linked.length - MAX_LINKED} more</li>}
          </ul>
        )}
        {links.source && (
          <p className="text-label text-cx-muted">
            From {links.source.startsWith('graph.bigquery') ? 'BigQuery Graph' : 'the local graph'}
            {links.seconds != null ? ` in ${links.seconds < 1 ? `${Math.round(links.seconds * 1000)} ms` : `${links.seconds.toFixed(1)} s`}` : ''}
          </p>
        )}
      </div>
    </div>
  );
}

export const workstationHref = (accountId: string): string =>
  `/cockpit?role=aml_investigator&entityId=${encodeURIComponent(accountId)}`;
export const mapHref = (accountId: string): string =>
  `/cockpit/geospatial?view=logins&sel=${encodeURIComponent(`account:${accountId}`)}`;
