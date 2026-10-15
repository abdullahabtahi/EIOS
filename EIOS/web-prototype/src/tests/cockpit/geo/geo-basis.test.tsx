import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import React from 'react';
import { REFERENCE } from './reference-fixture';
import { FLOWS } from './flows-fixture';
import type { GeoReference, ReferenceCountry } from '@/components/cockpit/geo/geo-types';

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
import { areaTier, BASES, DEFAULT_BASIS } from '@/components/cockpit/geo/geo-basis';
import { describeSelection } from '@/components/cockpit/geo/geo-format';
import { leadsFor } from '@/components/cockpit/geo/geo-leads';
import { summarizeReference } from '@/components/cockpit/geo/geo-aggregates';
import { parseGeoUrl, formatGeoUrl } from '@/components/cockpit/geo/geo-url';
import { GeoLegend } from '@/components/cockpit/geo/geo-legend';
import { GeoSources } from '@/components/cockpit/geo/geo-sources';

const base = REFERENCE.countries[0];
const extra = (over: Partial<ReferenceCountry> & Pick<ReferenceCountry, 'iso2' | 'name'>): ReferenceCountry => ({ ...base, fatf_list: null, eu_high_risk: false, basel: null, entities_incorporated: null, entities_linked: null, indicators: [], ...over });
/** The fixture plus Myanmar (on FATF, the EU list and rated highest by Basel) and Russia (EU list only, not rated). */
const WORLD: GeoReference = {
  ...REFERENCE,
  countries: [
    ...REFERENCE.countries,
    extra({ iso2: 'MM', name: 'Myanmar', fatf_list: 'call_for_action', eu_high_risk: true, basel: { score: 8.18, rank: 1, of: 177, band: 'higher' } }),
    extra({ iso2: 'RU', name: 'Russia', eu_high_risk: true }),
  ],
};
const country = (code: string) => WORLD.countries.find((c) => c.iso2 === code)!;

describe('risk basis', () => {
  it('opens on FATF, the basis the map used before', () => {
    expect(DEFAULT_BASIS).toBe('fatf');
    expect(BASES.map((b) => b.id)).toEqual(['fatf', 'eu', 'basel']);
  });

  it('maps each basis to a tier, and an unrated country to none (never low)', () => {
    expect(areaTier(country('IR'), 'fatf')).toBe('high');
    expect(areaTier(country('KE'), 'fatf')).toBe('medium');
    expect(areaTier(country('RU'), 'fatf')).toBeNull();
    expect(areaTier(country('RU'), 'eu')).toBe('medium');
    expect(areaTier(country('NO'), 'eu')).toBeNull();
    expect(areaTier(country('MM'), 'basel')).toBe('high');
    expect(areaTier(country('PA'), 'basel')).toBe('medium');
    expect(areaTier(country('NO'), 'basel')).toBe('low');
    expect(areaTier(country('RU'), 'basel')).toBeNull(); // not in the public index
  });
});

describe('country card', () => {
  const rows = (code: string) => Object.fromEntries(describeSelection(null, WORLD, { kind: 'country', id: code })!.rows);

  it('says which lists the country is on and what Basel gives it', () => {
    expect(rows('MM')['EU high-risk list']).toBe('Listed');
    expect(rows('NO')['EU high-risk list']).toBe('Not listed');
    expect(rows('PA')['Basel AML Index']).toBe('5.83 of 10 · Medium · rank 51 of 177');
    expect(rows('MM')['Basel AML Index']).toBe('8.18 of 10 · Higher · rank 1 of 177');
  });

  it('says "Not in the public index" rather than showing a score or a zero', () => {
    expect(rows('RU')['Basel AML Index']).toBe('Not in the public index');
  });
});

describe('leads per basis', () => {
  it('EU: separates the EU\'s own entries from those it shares with FATF', () => {
    const leads = leadsFor('jurisdictions', null, WORLD, 'eu')!;
    const group = (g: string) => leads.filter((l) => l.group === g).map((l) => l.title);
    expect(group('On the EU list, not on the FATF lists')).toEqual(['Russia']);
    expect(group('On the EU list and a FATF list').sort()).toEqual(['Iran', 'Kenya', 'Myanmar']);
  });

  it('Basel: the highest scores first, each with its rank', () => {
    const leads = leadsFor('jurisdictions', null, WORLD, 'basel')!;
    expect(leads[0]).toMatchObject({ title: 'Myanmar', tier: 'high', detail: '8.18 of 10 · rank 1 of 177' });
    expect(leads.map((l) => l.title)).not.toContain('Russia');
  });

  it('FATF: unchanged', () => {
    const groups = new Set(leadsFor('jurisdictions', null, WORLD, 'fatf')!.map((l) => l.group));
    expect(groups).toEqual(new Set(['On the FATF call-for-action list', 'Largest offshore centres']));
  });
});

describe('summary and url', () => {
  it('counts each basis from the same reference', () => {
    const s = summarizeReference(WORLD)!;
    expect(s.eu).toEqual({ listed: 4, alsoFatf: 3, euOnly: 1 });
    expect(s.basel).toEqual({ rated: 4, higher: 1, medium: 2, lower: 1 });
  });

  it('keeps the basis in the address bar only when it is not the default', () => {
    expect(parseGeoUrl('?view=jurisdictions&basis=eu').basis).toBe('eu');
    expect(parseGeoUrl('?basis=nonsense').basis).toBeNull();
    expect(formatGeoUrl('', 'jurisdictions', null, 'basel')).toBe('?view=jurisdictions&basis=basel');
    expect(formatGeoUrl('?basis=eu', 'jurisdictions', null, 'fatf')).toBe('?view=jurisdictions');
    expect(formatGeoUrl('?basis=eu', 'corridors', null, 'eu')).toBe('?view=corridors');
  });
});

describe('legend and sources', () => {
  const legend = (basis: 'fatf' | 'eu' | 'basel') => {
    render(<GeoLegend visible={new Set(['risk'])} flows={FLOWS} basis={basis} />);
    return within(screen.getByRole('list', { name: 'Map legend' })).getAllByRole('listitem').map((li) => li.textContent);
  };
  it('names the marks of the basis in use only', () => {
    expect(legend('eu')).toEqual(['On the EU high-risk list']);
  });
  it('Basel: the three bands with the Institute\'s breaks, and what no fill means', () => {
    const items = legend('basel');
    expect(items).toEqual(['Higher risk (above 6.08)', 'Medium risk (4.70 to 6.08)', 'Lower risk (below 4.70)', 'No fill: not in the public index']);
  });

  it('credits the EU Commission and the Basel Institute with links', () => {
    render(<GeoSources flows={FLOWS} reference={WORLD} />);
    expect(screen.getByRole('link', { name: /Basel AML Index 2025/ })).toHaveAttribute('href', 'https://index.baselgovernance.org');
    expect(screen.getByRole('link', { name: /EU high-risk third countries/ })).toHaveAttribute('href', expect.stringContaining('finance.ec.europa.eu'));
  });
});

describe('workspace', () => {
  beforeEach(() => {
    window.history.replaceState(null, '', '/');
    authFetch.mockReset();
    authFetch.mockImplementation(async (url: string) => ({ ok: true, status: 200, json: async () => (url.includes('/geo/flows') ? FLOWS : WORLD) }));
  });

  it('offers the basis switch in Jurisdictions only, and it changes the list and the legend', async () => {
    render(<GeoWorkspace />);
    await screen.findByRole('region', { name: 'Where to look first' });
    expect(screen.queryByRole('group', { name: 'Risk basis' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Jurisdictions' }));
    const basis = screen.getByRole('group', { name: 'Risk basis' });
    expect(within(basis).getByRole('button', { name: 'FATF' })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(within(basis).getByRole('button', { name: 'Basel AML' }));
    expect(within(basis).getByRole('button', { name: 'Basel AML' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Higher risk (above 6.08)')).toBeInTheDocument();
    expect(within(screen.getByRole('region', { name: 'Where to look first' })).getByText('Myanmar')).toBeInTheDocument();
    expect(window.location.search).toContain('basis=basel');
  });
});
