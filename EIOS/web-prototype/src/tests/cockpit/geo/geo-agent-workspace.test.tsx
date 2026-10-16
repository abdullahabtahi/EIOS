import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
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

const ANSWER = {
  queryId: 'q1',
  naturalLanguageQuery: 'where?',
  responseMarkdown: 'Start with the shared exit in Kenya.',
  citedMetrics: [],
  assistantStatus: 'ASSEMBLED',
  blocked: false,
  steps: ['get_geo_overview'],
  proposals: [],
  viewCommands: [{ kind: 'gateway', id: 'GW-KE-X00' }],
  timestamp: '2026-10-16T00:00:00Z',
};
const LIST_CHANGE = {
  list_id: 'fatf',
  as_of: '2026-10-14T08:00:00+00:00',
  source: 'AML engine',
  before: { label: 'FATF lists, February 2026 plenary', in_force: 'February to June 2026', source: 'derived' },
  after: { label: 'FATF lists, June 2026 plenary', in_force: 'from 2026-06-19', source: 'FATF' },
  added: {
    countries: [
      {
        iso2: 'KE', name: 'Kenya', before: null, after: 'increased_monitoring', registered_accounts: 0, login_accounts: 3,
        sessions: 9, payment_accounts: 0, payment_volume_usd: 0, shared_exits: ['GW-KE-X00'], exposed_accounts: 3, linked_accounts: 2,
      },
    ],
    exposed_accounts: 3, sessions: 9, payment_volume_usd: 0, session_shares: { KE: 100 }, payment_shares: null,
  },
  removed: { countries: [], exposed_accounts: 0, sessions: 0, payment_volume_usd: 0, session_shares: null, payment_shares: null },
  relisted: { countries: [], exposed_accounts: 0, sessions: 0, payment_volume_usd: 0, session_shares: null, payment_shares: null },
  graph: { source: 'graph.bigquery:p.warm_graph.aml_geo', seconds: 1.8, error: null },
};

type Reply = { status: number; body?: unknown };
const ROUTES: Record<string, Reply> = {
  '/geo/reference': { status: 200, body: REFERENCE },
  '/geo/flows': { status: 200, body: { ...FLOWS, gateways: [GATEWAY], hubs_suppressed: 1 } },
  '/geo/accounts/': { status: 200, body: ACCOUNT },
  '/geo/list-changes': { status: 200, body: LIST_CHANGE },
  '/copilot/models': { status: 200, body: { models: [] } },
  '/copilot/query': { status: 200, body: ANSWER },
};

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  authFetch.mockReset();
  authFetch.mockImplementation(async (url: string) => {
    const key = Object.keys(ROUTES).find((k) => url.includes(k)) ?? '';
    const r = ROUTES[key] ?? { status: 404 };
    return { ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.body ?? {} };
  });
});

describe('the assistant on the map', () => {
  it('moves the map to what the answer names, says so, and goes back', async () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(screen.getByRole('tab', { name: 'Ask' }));
    fireEvent.click(await screen.findByText('Where should I look first?'));
    await waitFor(() => expect(window.location.search).toContain('sel=gateway%3AGW-KE-X00'));
    expect(window.location.search).toContain('view=logins');
    expect(screen.getByText(/The assistant moved the map to/)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Back'));
    await waitFor(() => expect(window.location.search).not.toContain('sel='));
    expect(window.location.search).toContain('view=corridors');
  });

  it('carries what the map shows with the question', async () => {
    render(<GeoWorkspace initialSearch="?view=logins&sel=gateway:GW-KE-X00" />);
    fireEvent.click(screen.getByRole('tab', { name: 'Ask' }));
    fireEvent.click(await screen.findByText('Why is this exit suspicious, and who else is in its ring?'));
    await waitFor(() => expect(authFetch.mock.calls.some(([url]) => String(url).includes('/copilot/query'))).toBe(true));
    const [, init] = authFetch.mock.calls.find(([url]) => String(url).includes('/copilot/query'))!;
    expect(JSON.parse(init.body).mapContext).toEqual({ view: 'logins', selection: { kind: 'gateway', id: 'GW-KE-X00' } });
  });
});

describe('what the latest list change does to us', () => {
  it('opens from the mode switch and shows the countries the change names, most exposed first', async () => {
    render(<GeoWorkspace initialSearch="?view=jurisdictions" />);
    fireEvent.click(await screen.findByRole('button', { name: /What changed/ }));
    const region = await screen.findByRole('region', { name: 'What changed on the lists' });
    expect(await within(region).findByText('Kenya')).toBeInTheDocument();
    expect(within(region).getByText(/Links from BigQuery Graph in 1.8 s/)).toBeInTheDocument();
    fireEvent.click(within(region).getByRole('button', { name: /Kenya/ }));
    expect(within(region).getByText('Shared exit here: GW-KE-X00')).toBeInTheDocument();
    await waitFor(() => expect(window.location.search).toContain('sel=country%3AKE'));
  });
});
