'use client';

import * as React from 'react';
import { authFetch } from '@/lib/auth/token';
import type { AddressListName, AddressVerdict, GeoAddress } from './geo-types';

const ENDPOINT = '/api/cockpit/geo/address';
const VERDICT_TEXT: Readonly<Record<Exclude<AddressVerdict, 'not_public'>, string>> = {
  tor_exit: 'On the Tor exit list',
  vpn: 'On a VPN list',
  cloud: "Inside a cloud provider's range",
  datacenter: 'On a datacenter list',
  none_listed: 'Not on any list we hold',
};
const LIST_TEXT: Readonly<Record<AddressListName, string>> = { tor_exit: 'Tor', vpn: 'VPN', cloud: 'cloud', datacenter: 'datacenter' };
const SCOPE_TEXT: Readonly<Record<string, string>> = {
  private: 'a private address',
  loopback: 'a loopback address',
  link_local: 'a link-local address',
  multicast: 'a multicast address',
  unspecified: 'an unspecified address',
  reserved: 'a reserved address',
};

const matchText = (list: AddressListName, detail: string): string =>
  list === 'tor_exit' ? 'Tor exit relay' : list === 'vpn' ? 'VPN range' : list === 'datacenter' ? 'Datacenter range' : `Cloud range: ${detail}`;

const joinNames = (names: readonly string[]): string => (names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`);

type State =
  | { readonly status: 'idle' }
  | { readonly status: 'loading' }
  | { readonly status: 'error'; readonly message: string }
  | { readonly status: 'ready'; readonly result: GeoAddress };

async function lookup(address: string): Promise<State> {
  try {
    const res = await authFetch(ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ address }) });
    if (res.ok) return { status: 'ready', result: (await res.json()) as GeoAddress };
    if (res.status === 422) return { status: 'error', message: 'That is not an IP address. Use an IPv4 or IPv6 address, for example 203.0.113.7.' };
    if (res.status === 503) return { status: 'error', message: 'This environment has no network data loaded, so no address can be checked here.' };
    return { status: 'error', message: `The check failed (HTTP ${res.status}). Try again.` };
  } catch {
    return { status: 'error', message: 'The check could not reach the service. Try again.' };
  }
}

function Row({ label, children }: { readonly label: string; readonly children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="shrink-0 text-cx-muted">{label}</dt>
      <dd className="text-right text-cx-ink">{children}</dd>
    </div>
  );
}

function Result({ result, onShowCountry, knownCountries }: { readonly result: GeoAddress; readonly onShowCountry?: (iso2: string) => void; readonly knownCountries?: ReadonlySet<string> }) {
  if (result.verdict === 'not_public') {
    return (
      <p className="text-xs text-cx-ink-soft">
        <span>{result.address}</span> is {SCOPE_TEXT[result.scope] ?? 'not a public address'}. It does not exist on the open internet, so nothing is looked up.
      </p>
    );
  }
  const elevated = result.verdict !== 'none_listed';
  const country = result.country;
  const canShow = country && onShowCountry && knownCountries?.has(country.iso2);
  return (
    <div className="space-y-2">
      <p className={`text-xs font-semibold ${elevated ? 'text-cx-bad' : 'text-cx-ink'}`}>{VERDICT_TEXT[result.verdict as Exclude<AddressVerdict, 'not_public'>]}</p>
      {!elevated && <p className="text-label text-cx-muted">That does not mean the address is clean, only that no list we hold names it.</p>}
      <dl className="space-y-1 text-xs">
        <Row label="Address"><span>{result.address}</span></Row>
        <Row label="Country">{country ? country.name : 'Not in the database'}</Row>
        {result.network && (
          <Row label="Network">{`AS${result.network.asn} · ${result.network.name}`}</Row>
        )}
        {result.lists.length > 0 && (
          <Row label="Listed in">
            <ul>
              {result.lists.map((m, i) => (
                <li key={`${m.list}-${i}`}>{matchText(m.list, m.detail)}</li>
              ))}
            </ul>
          </Row>
        )}
      </dl>
      {canShow && (
        <button
          type="button"
          onClick={() => onShowCountry(country.iso2)}
          className="cursor-pointer text-xs font-semibold text-cx-accent outline-none hover:text-cx-accent-strong focus-visible:ring-2 focus-visible:ring-cx-accent">
          {`Show ${country.name} on the map`}
        </button>
      )}
      {result.uncovered.length > 0 && (
        <p className="text-label text-cx-warn">
          The {joinNames(result.uncovered.map((l) => LIST_TEXT[l]))} lists hold no IPv{result.version} networks, so they cannot rule this address out.
        </p>
      )}
      <p className="text-label text-cx-muted">The country is where the address is registered, which a VPN or a proxy can hide.</p>
      <details className="text-label text-cx-muted">
        <summary className="cursor-pointer font-semibold text-cx-ink-soft outline-none focus-visible:ring-2 focus-visible:ring-cx-accent">Sources</summary>
        <ul className="mt-1 space-y-0.5">
          {result.sources.map((s) => (
            <li key={s.name}>{`${s.name} · as of ${s.as_of}`}</li>
          ))}
        </ul>
        <p className="mt-1">
          IP address data is powered by{' '}
          <a href="https://ipinfo.io" target="_blank" rel="noopener noreferrer" className="text-cx-accent underline underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-cx-accent">
            IPinfo
          </a>
          .
        </p>
      </details>
    </div>
  );
}

export interface GeoAddressCheckProps {
  readonly onShowCountry?: (iso2: string) => void;
  /** Countries the map can draw; "Show on the map" is offered only for these. */
  readonly knownCountries?: ReadonlySet<string>;
}

/** Type an IP address, get what the network reference and the public lists say about it. Nothing here keeps the address. */
export function GeoAddressCheck({ onShowCountry, knownCountries }: GeoAddressCheckProps) {
  const [value, setValue] = React.useState('');
  const [state, setState] = React.useState<State>({ status: 'idle' });
  const id = React.useId();
  const trimmed = value.trim();
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!trimmed) return;
    setState({ status: 'loading' });
    setState(await lookup(trimmed));
  };
  return (
    <section aria-label="Check an address" className="space-y-2">
      <form onSubmit={submit} className="space-y-1.5">
        <label htmlFor={id} className="block text-label font-semibold text-cx-ink-soft">
          IP address
        </label>
        <div className="flex gap-1.5">
          <input
            id={id}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            spellCheck={false}
            autoComplete="off"
            placeholder="203.0.113.7 or 2001:db8::1"
            className="min-w-0 flex-1 border border-cx-line bg-white px-2 py-1.5 text-xs text-cx-ink outline-none placeholder:text-cx-faint focus-visible:ring-2 focus-visible:ring-cx-accent"
          />
          <button
            type="submit"
            disabled={!trimmed || state.status === 'loading'}
            className="cursor-pointer border border-cx-line bg-white px-3 py-1.5 text-xs font-semibold text-cx-ink outline-none hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-cx-accent disabled:cursor-not-allowed disabled:text-cx-muted">
            Check
          </button>
        </div>
        <p className="text-label text-cx-muted">Checked here against public lists. The address is not stored.</p>
      </form>
      <div aria-live="polite">
        {state.status === 'loading' && <p className="text-xs text-cx-muted">Checking…</p>}
        {state.status === 'error' && (
          <p role="alert" className="border border-cx-warn-line bg-cx-warn-bg p-2 text-xs text-cx-ink-soft">
            {state.message}
          </p>
        )}
        {state.status === 'ready' && <Result result={state.result} onShowCountry={onShowCountry} knownCountries={knownCountries} />}
      </div>
    </section>
  );
}
