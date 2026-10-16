import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import React from 'react';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';
import { buildLayers } from '@/components/cockpit/geo/geo-layers';
import { beforeTiers, changeCount, listingTier } from '@/components/cockpit/geo/geo-compare';
import type { GeoListChange, LayerId, ListChangeCountry } from '@/components/cockpit/geo/geo-types';

vi.mock('@vis.gl/react-google-maps', () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Map: ({ children }: { children: React.ReactNode }) => <div data-testid="google-map">{children}</div>,
  useMap: () => null,
}));
vi.mock('@deck.gl/google-maps', () => ({
  GoogleMapsOverlay: class {
    setMap = vi.fn();
    setProps = vi.fn();
    finalize = vi.fn();
  },
}));
const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { GeoWorkspace } from '@/components/cockpit/geo/geo-workspace';

const country = (over: Partial<ListChangeCountry>): ListChangeCountry => ({
  iso2: 'XX', name: 'Nowhere', before: null, after: null, registered_accounts: 0, login_accounts: 0, sessions: 0,
  payment_accounts: 0, payment_volume_usd: 0, shared_exits: [], exposed_accounts: 0, linked_accounts: 0, ...over,
});
const empty = { countries: [], exposed_accounts: 0, sessions: 0, payment_volume_usd: 0, session_shares: null, payment_shares: null };
const CHANGE: GeoListChange = {
  list_id: 'fatf',
  as_of: '2026-10-14T08:00:00+00:00',
  source: 'AML engine',
  before: { label: 'FATF lists, February 2026 plenary', in_force: 'February to June 2026', source: 'derived' },
  after: { label: 'FATF lists, June 2026 plenary', in_force: 'from 2026-06-19', source: 'FATF' },
  added: { ...empty, countries: [country({ iso2: 'KE', name: 'Kenya', after: 'increased_monitoring', login_accounts: 3, sessions: 9, exposed_accounts: 3 })], exposed_accounts: 3, sessions: 9, session_shares: { KE: 100 } },
  removed: { ...empty, countries: [country({ iso2: 'IR', name: 'Iran', before: 'call_for_action', exposed_accounts: 5 })], exposed_accounts: 5 },
  relisted: empty,
  graph: { source: 'graph.bigquery:p.warm_graph.aml_geo', seconds: 1.8, error: null },
};

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  authFetch.mockReset();
  authFetch.mockImplementation(async (url: string) => {
    const body = url.includes('/geo/reference') ? REFERENCE : url.includes('/geo/list-changes') ? CHANGE : url.includes('/geo/flows') ? FLOWS : {};
    return { ok: true, status: 200, json: async () => body };
  });
});

describe('reading a list change as map tiers', () => {
  it('maps a listing to the tier the map draws, and none to unrated', () => {
    expect(listingTier('call_for_action')).toBe('high');
    expect(listingTier('increased_monitoring')).toBe('medium');
    expect(listingTier('eu_high_risk')).toBe('medium');
    expect(listingTier(null)).toBeNull();
    expect(listingTier('something_new')).toBeNull();
  });

  it('counts every country the change names, added, removed or moved', () => {
    expect(changeCount(CHANGE)).toBe(2);
  });

  it('gives the tier each changed country had before, and names no other', () => {
    const before = beforeTiers(CHANGE);
    expect(before.get('IR')).toBe('high');
    expect(before.get('KE')).toBeNull();
    expect(before.has('NO')).toBe(false);
  });

  it('recolours the map with the earlier edition, only for the countries that changed', () => {
    const ALL = new Set<LayerId>(['risk']);
    const fill = (override: ReturnType<typeof beforeTiers> | null, iso2: string) => {
      const layer = buildLayers(FLOWS, REFERENCE, ALL, null, {}, [], 'fatf', null, override).find((l) => l.id === 'geo-risk')!;
      const data = layer.props.data as unknown as { properties: { country: { iso2: string } } }[];
      const accessor = (layer.props as unknown as { getFillColor: (f: unknown) => number[] }).getFillColor;
      return accessor(data.find((f) => f.properties.country.iso2 === iso2)!);
    };
    expect(fill(null, 'IR')[3]).toBeGreaterThan(0); // listed now: drawn
    const before = new Map([['IR', null as null], ['KE', 'high' as const]]);
    expect(fill(before, 'IR')[3]).toBe(0); // not listed before: nothing
    expect(fill(before, 'KE')[3]).toBeGreaterThan(0);
    expect(fill(before, 'NO')).toEqual(fill(null, 'NO')); // unchanged countries keep today's colour
  });
});

describe('the comparison in the Jurisdictions view', () => {
  const open = async () => {
    render(<GeoWorkspace initialSearch="?view=jurisdictions" />);
    return screen.findByRole('button', { name: /Compare FATF/ });
  };

  it('puts the number of changed countries on the list it concerns, and none on a list without a change', async () => {
    const badge = await open();
    expect(badge).toHaveTextContent('2');
    expect(screen.getByRole('button', { name: /Compare EU/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Compare Basel/ })).toBeNull();
  });

  it('no longer offers the old full-width bar', async () => {
    await open();
    expect(screen.queryByText('What did the latest list change do to us?')).toBeNull();
  });

  it('opens the table and the Before and After switch from the badge', async () => {
    fireEvent.click(await open());
    const region = await screen.findByRole('region', { name: 'What changed on the lists' });
    expect(await within(region).findByText('Kenya')).toBeInTheDocument();
    const after = screen.getByRole('button', { name: 'After' });
    const before = screen.getByRole('button', { name: 'Before' });
    expect(after).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(before);
    expect(before).toHaveAttribute('aria-pressed', 'true');
    expect(after).toHaveAttribute('aria-pressed', 'false');
  });

  it('closes from the panel, and when the basis moves to a list with no change', async () => {
    fireEvent.click(await open());
    await screen.findByRole('region', { name: 'What changed on the lists' });
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('region', { name: 'What changed on the lists' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Compare FATF/ }));
    await screen.findByRole('region', { name: 'What changed on the lists' });
    fireEvent.click(screen.getByRole('button', { name: 'Basel AML' }));
    await waitFor(() => expect(screen.queryByRole('region', { name: 'What changed on the lists' })).toBeNull());
    expect(screen.queryByRole('button', { name: 'Before' })).toBeNull();
  });

  it('follows the basis to the other list while a comparison is open', async () => {
    fireEvent.click(await open());
    await screen.findByRole('region', { name: 'What changed on the lists' });
    fireEvent.click(screen.getByRole('button', { name: 'EU' }));
    await waitFor(() => expect(screen.getByRole('region', { name: 'What changed on the lists' })).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Compare EU/ })).toHaveAttribute('aria-pressed', 'true');
  });
});
