import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import React from 'react';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';
import { buildLayers } from '@/components/cockpit/geo/geo-layers';
import { beforeTiers, changeCount, changeNotes, listingTier, withChangeNote } from '@/components/cockpit/geo/geo-compare';
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

describe('what a change says about one country', () => {
  it('says what happened to each country the change names, and nothing about the rest', () => {
    const notes = changeNotes(CHANGE);
    expect(notes.get('KE')).toBe('Added · increased monitoring');
    expect(notes.get('IR')).toBe('Removed · was call for action');
    expect(notes.has('NO')).toBe(false);
  });

  it('adds the latest change to a country description without altering the original', () => {
    const view = { title: 'Kenya', rows: [['FATF list', 'Increased monitoring']] as const };
    const out = withChangeNote(view, 'Added · increased monitoring');
    expect(out.rows.at(-1)).toEqual(['Latest change', 'Added · increased monitoring']);
    expect(out.changed).toBe(true);
    expect(view.rows).toHaveLength(1);
    expect(withChangeNote(view, undefined)).toBe(view);
  });
});

describe('the Jurisdictions view and what changed on its lists', () => {
  const open = async () => {
    render(<GeoWorkspace initialSearch="?view=jurisdictions" />);
    return screen.findByRole('button', { name: /What changed/ });
  };
  const region = () => screen.getByRole('region', { name: 'What changed on the lists' });

  it('puts one icon toggle at the far right of the list switcher row, with the count for the list in view, and no second switch', async () => {
    const toggle = await open();
    expect(toggle).toHaveTextContent('2');
    expect(toggle).toHaveAttribute('aria-pressed', 'false');
    // It sits on the switcher row itself, not in a second control.
    expect(within(screen.getByRole('group', { name: 'Risk basis' })).getByRole('button', { name: 'FATF' }).parentElement?.parentElement).toContainElement(toggle);
    expect(screen.queryByRole('button', { name: /Where we stand/ })).toBeNull();
    expect(screen.queryByRole('group', { name: 'Which list' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'What changed on the lists' })).toBeNull();
  });

  it('opens the table and the Before and After switch, keeps the list switcher, and puts the summary and the lead list away', async () => {
    fireEvent.click(await open());
    expect(await within(await screen.findByRole('region', { name: 'What changed on the lists' })).findByText('Kenya')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /What changed/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'FATF' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'After' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByRole('region', { name: 'Where to look first' })).toBeNull();
  });

  it('switches Before and After', async () => {
    fireEvent.click(await open());
    await screen.findByRole('region', { name: 'What changed on the lists' });
    fireEvent.click(screen.getByRole('button', { name: 'Before' }));
    expect(screen.getByRole('button', { name: 'Before' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'After' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('follows the list switcher to the other list, and ends on Basel, which has no change to read', async () => {
    fireEvent.click(await open());
    await screen.findByRole('region', { name: 'What changed on the lists' });
    fireEvent.click(screen.getByRole('button', { name: 'EU' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'EU' })).toHaveAttribute('aria-pressed', 'true'));
    expect(region()).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Basel AML' }));
    await waitFor(() => expect(screen.queryByRole('region', { name: 'What changed on the lists' })).toBeNull());
    expect(screen.queryByRole('button', { name: /What changed/ })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Before' })).toBeNull();
  });

  it('closes with the same toggle and goes back to the lists as they stand', async () => {
    fireEvent.click(await open());
    await screen.findByRole('region', { name: 'What changed on the lists' });
    fireEvent.click(screen.getByRole('button', { name: /What changed/ }));
    expect(screen.queryByRole('region', { name: 'What changed on the lists' })).toBeNull();
    expect(screen.getByRole('region', { name: 'Where to look first' })).toBeInTheDocument();
  });

  it('names the outlines on the map in the legend, for a list that has a change, and not for Basel', async () => {
    await open();
    const legend = screen.getByRole('list', { name: 'Map legend' });
    expect(within(legend).getByText('Added to the list')).toBeInTheDocument();
    expect(within(legend).getByText('Removed from the list')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Basel AML' }));
    expect(within(screen.getByRole('list', { name: 'Map legend' })).queryByText('Added to the list')).toBeNull();
  });

  it('says on a country that it changed, and opens the comparison from there', async () => {
    render(<GeoWorkspace initialSearch="?view=jurisdictions&sel=country:KE" />);
    const detail = await screen.findByRole('region', { name: 'Selection' });
    await waitFor(() => expect(within(detail).getByText('Latest change')).toBeInTheDocument());
    expect(within(detail).getByText('Added · increased monitoring')).toBeInTheDocument();
    fireEvent.click(within(detail).getByRole('button', { name: 'See what changed' }));
    expect(await screen.findByRole('region', { name: 'What changed on the lists' })).toBeInTheDocument();
  });
});
