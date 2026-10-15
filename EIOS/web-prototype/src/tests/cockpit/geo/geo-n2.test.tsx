import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import React from 'react';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';
import { ACCOUNT, GATEWAY } from './account-fixture';

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
vi.mock('next/link', () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => <a href={href} {...rest}>{children}</a>,
}));
const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { GeoWorkspace } from '@/components/cockpit/geo/geo-workspace';
import { GeoDossierCard } from '@/components/cockpit/geo/geo-dossier-card';
import { accountFacts } from '@/components/cockpit/geo/geo-account';
import { leadsFor } from '@/components/cockpit/geo/geo-leads';
import { describeSelection } from '@/components/cockpit/geo/geo-format';
import { cameraForCodes } from '@/components/cockpit/geo/geo-camera';
import { buildLayers } from '@/components/cockpit/geo/geo-layers';
import type { LayerId } from '@/components/cockpit/geo/geo-types';

const WITH_EXITS = { ...FLOWS, gateways: [GATEWAY], hubs_suppressed: 1 };
type Reply = { status: number; body?: unknown };
function serve(routes: Record<string, Reply>) {
  authFetch.mockImplementation(async (url: string) => {
    const key = Object.keys(routes).find((k) => url.includes(k)) ?? '';
    const r = routes[key] ?? { status: 404 };
    return { ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.body ?? {} };
  });
}
const DEFAULT = { '/geo/reference': { status: 200, body: REFERENCE }, '/geo/flows': { status: 200, body: WITH_EXITS }, '/geo/accounts/': { status: 200, body: ACCOUNT } };

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  authFetch.mockReset();
  serve(DEFAULT);
});

describe('shared exits on the map', () => {
  it('lists shared exits first in the login view, then the country pairs', () => {
    const leads = leadsFor('logins', WITH_EXITS, REFERENCE)!;
    expect(leads[0]).toMatchObject({ group: 'Shared foreign exits', title: 'Shared exit in Kenya', tier: 'high' });
    expect(leads[0].detail).toBe('3 accounts from 2 countries · 7 impossible jumps');
    expect(leads[1].group).toBe('Registered here, logging in there');
  });

  it('describes an exit with who uses it, from where, the hubs set aside, and its accounts', () => {
    const view = describeSelection(WITH_EXITS, REFERENCE, { kind: 'gateway', id: 'GW-KE-X00' })!;
    expect(view.title).toBe('Shared exit in Kenya');
    expect(view.rows).toContainEqual(['Registered in', 'Norway 2, Panama 1']);
    expect(view.accounts).toEqual(GATEWAY.sample_accounts);
    expect(view.note).toMatch(/1 gateway shared by more than 100 accounts was set aside as hubs \(RL-4\)/);
  });

  it('frames a set of countries, and nothing when none can be placed', () => {
    const t = cameraForCodes(['KE', 'NO', 'PA'], REFERENCE)!;
    expect(t.kind).toBe('bounds');
    expect(cameraForCodes(['ZZ'], REFERENCE)).toBeNull();
    expect(cameraForCodes(['KE'], REFERENCE)?.kind).toBe('point');
  });

  it('draws the pick above every lens and skips arcs it cannot place', () => {
    const layers = buildLayers(WITH_EXITS, REFERENCE, new Set<LayerId>(['mismatches']), null, {}, [
      { from: 'NO', to: 'KE', weight: 2 },
      { from: 'ZZ', to: 'KE', weight: 1 },
    ]);
    const top = layers[layers.length - 1];
    expect(top.id).toBe('geo-highlight');
    expect((top.props.data as unknown[]).length).toBe(1);
  });
});

describe('an account on the map', () => {
  it('opens from an exit, shows its geography and graph links, and links to its case', async () => {
    window.history.replaceState(null, '', '/?view=logins');
    render(<GeoWorkspace />);
    const list = await screen.findByRole('region', { name: 'Where to look first' });
    fireEvent.click(within(list).getByRole('button', { name: /Shared exit in Kenya/ }));
    fireEvent.click(within(screen.getByRole('region', { name: 'Selection' })).getByRole('button', { name: 'CR84920' }));
    const detail = await screen.findByRole('region', { name: 'Selection' });
    await waitFor(() => expect(detail).toHaveTextContent('Registered in'));
    expect(detail).toHaveTextContent('Kenya 9 of 12');
    expect(detail).toHaveTextContent('GW-KE-X00, used by 3 accounts');
    expect(detail).toHaveTextContent('2 jumps, e.g. Norway to Kenya, 7,120 km in 2.5 h');
    expect(detail).toHaveTextContent('Linked accounts (2)');
    expect(detail).toHaveTextContent('From BigQuery Graph in 1.8 s');
    expect(within(detail).getByRole('link', { name: /Open the case in the AML workstation/ })).toHaveAttribute(
      'href',
      '/cockpit?role=aml_investigator&entityId=CR84920',
    );
    expect(window.location.search).toContain('sel=account%3ACR84920');
  });

  it('moves to a linked account in one click', async () => {
    window.history.replaceState(null, '', '/?view=logins&sel=account%3ACR84920');
    render(<GeoWorkspace />);
    const detail = await screen.findByRole('region', { name: 'Selection' });
    await waitFor(() => expect(within(detail).getByRole('button', { name: 'CR11111' })).toBeInTheDocument());
    fireEvent.click(within(detail).getByRole('button', { name: 'CR11111' }));
    expect(screen.getByRole('heading', { level: 3, name: 'CR11111' })).toBeInTheDocument();
    expect(authFetch).toHaveBeenCalledWith('/api/cockpit/geo/accounts/CR11111', expect.anything());
  });

  it('says so when the graph could not answer, and keeps the rest of the evidence', async () => {
    serve({ ...DEFAULT, '/geo/accounts/': { status: 200, body: { ...ACCOUNT, neighbourhood: { source: null, rows: null, error: 'warehouse unreachable' } } } });
    window.history.replaceState(null, '', '/?view=logins&sel=account%3ACR84920');
    render(<GeoWorkspace />);
    const detail = await screen.findByRole('region', { name: 'Selection' });
    await waitFor(() => expect(detail).toHaveTextContent('The graph could not answer: warehouse unreachable'));
    expect(detail).toHaveTextContent('GW-KE-X00, used by 3 accounts');
  });

  it('tells an unknown account apart from an outage', async () => {
    serve({ ...DEFAULT, '/geo/accounts/': { status: 404 } });
    window.history.replaceState(null, '', '/?view=logins&sel=account%3ACR99999');
    render(<GeoWorkspace />);
    expect(await screen.findByText('No account CR99999 in this world.')).toBeInTheDocument();
  });
});

describe('accountFacts', () => {
  it('says not assessable, never none, when the travel lens could not run', () => {
    const facts = Object.fromEntries(accountFacts({ ...ACCOUNT, jumps: null }));
    expect(facts['Impossible travel']).toBe('not assessable');
    expect(Object.fromEntries(accountFacts({ ...ACCOUNT, jumps: { count: 0, via_hub: 0, examples: [] } }))['Impossible travel']).toBe('none');
  });

  it('names the cross-border money with its direction', () => {
    expect(Object.fromEntries(accountFacts(ACCOUNT))['Cross-border money']).toBe('Iran out $4K');
  });
});

describe('GeoDossierCard', () => {
  it('shows the account geography in the dossier, flagged, with a link onto the map', async () => {
    render(<GeoDossierCard entityId="CR84920" />);
    const card = await screen.findByRole('region', { name: 'Geography' });
    await waitFor(() => expect(card).toHaveTextContent('FLAGGED'));
    expect(card).toHaveTextContent('Kenya 9 of 12');
    expect(within(card).getByRole('link', { name: /Open in map/ })).toHaveAttribute(
      'href',
      '/cockpit/geospatial?view=logins&sel=account%3ACR84920',
    );
  });

  it('shows nothing for an unknown account or a non-account entity, and an alert for an outage', async () => {
    serve({ '/geo/accounts/': { status: 404 } });
    const { container, unmount } = render(<GeoDossierCard entityId="CR99999" />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
    unmount();
    render(<GeoDossierCard entityId="PARTNER-7" />);
    expect(authFetch).toHaveBeenCalledTimes(1);
    serve({ '/geo/accounts/': { status: 503 } });
    render(<GeoDossierCard entityId="CR84920" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Geography could not be loaded (HTTP 503)');
  });
});
