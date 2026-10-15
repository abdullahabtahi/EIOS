import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import React from 'react';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';

vi.mock('@vis.gl/react-google-maps', () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="api-provider">{children}</div>,
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
import { describeSelection } from '@/components/cockpit/geo/geo-format';

type Reply = { status: number; body?: unknown };
/** Route the two endpoints independently, as the backend does. */
function serve(reference: Reply, flows: Reply) {
  authFetch.mockImplementation(async (url: string) => {
    const r = url.includes('/geo/flows') ? flows : reference;
    return { ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.body ?? {} };
  });
}
const OK = (body: unknown): Reply => ({ status: 200, body });
const DOWN: Reply = { status: 503 };

beforeEach(() => {
  vi.unstubAllEnvs();
  authFetch.mockReset();
  serve(OK(REFERENCE), OK(FLOWS));
});
afterEach(() => vi.unstubAllEnvs());

const MANY_FLOWS = {
  ...FLOWS,
  corridors: [
    ...FLOWS.corridors,
    ...Array.from({ length: 10 }, (_, i) => ({ origin: 'PA', destination: 'BS', volume_usd: 1_000 + i, accounts: 1, events: 1, tier: 'low' as const })),
  ],
};

const tab = (name: string) => screen.getByRole('tab', { name });

describe('GeoWorkspace', () => {
  it('says the map is unavailable, rather than rendering blank, when no key is configured', () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_MAPS_API_KEY', '');
    render(<GeoWorkspace />);
    expect(screen.getByText('Map unavailable')).toBeInTheDocument();
    expect(screen.queryByTestId('google-map')).not.toBeInTheDocument();
  });

  it('renders the Google map when a key is configured', () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_MAPS_API_KEY', 'test-key');
    render(<GeoWorkspace />);
    expect(screen.getByTestId('google-map')).toBeInTheDocument();
  });

  it('opens on one question, with only that view in the legend', async () => {
    render(<GeoWorkspace />);
    expect(tab('Corridors')).toHaveAttribute('aria-selected', 'true');
    expect(await screen.findByRole('heading', { level: 2, name: /Where does money cross borders/ })).toBeInTheDocument();
    const legend = screen.getByRole('list', { name: 'Map legend' });
    expect(within(legend).getByText('High-risk corridor')).toBeInTheDocument();
    expect(within(legend).getByText('FATF call for action')).toBeInTheDocument();
    expect(within(legend).queryByText(/Offshore entities/)).not.toBeInTheDocument();
    expect(within(legend).queryByText(/Registered here/)).not.toBeInTheDocument();
  });

  it('carries no data-origin labels and no unconnected placeholder on first view', async () => {
    render(<GeoWorkspace />);
    await screen.findByRole('region', { name: 'Where to look first' });
    for (const word of [/^Engine$/i, /^Reference$/i, /Not connected/i, /Geo copilot/i, /Evidence lenses/i]) {
      expect(screen.queryByText(word)).not.toBeInTheDocument();
    }
  });

  it('lists where to look first, elevated corridors on top, and says how much the map draws', async () => {
    render(<GeoWorkspace />);
    const list = await screen.findByRole('region', { name: 'Where to look first' });
    const rows = within(list).getAllByRole('button');
    expect(rows[0]).toHaveTextContent('Norway → Iran');
    expect(rows[0]).toHaveTextContent('High');
    expect(rows[1]).toHaveTextContent('Kenya → The Bahamas');
    expect(screen.getByRole('list', { name: 'Map legend' }).parentElement).toHaveTextContent('Showing 3 of 3 corridors');
  });

  it('pins a lead into the panel with its full facts, and puts it down again', async () => {
    render(<GeoWorkspace />);
    const list = await screen.findByRole('region', { name: 'Where to look first' });
    fireEvent.click(within(list).getByRole('button', { name: /Norway → Iran/ }));
    const detail = screen.getByRole('region', { name: 'Selection' });
    expect(detail).toHaveTextContent('Risk tier');
    expect(detail).toHaveTextContent('$900K');
    expect(within(list).getByRole('button', { name: /Norway → Iran/ })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(within(detail).getByRole('button', { name: 'Clear selection' }));
    expect(screen.queryByRole('region', { name: 'Selection' })).not.toBeInTheDocument();
  });

  it('clears a selection with Escape', async () => {
    render(<GeoWorkspace />);
    const list = await screen.findByRole('region', { name: 'Where to look first' });
    fireEvent.click(within(list).getByRole('button', { name: /Kenya → The Bahamas/ }));
    expect(screen.getByRole('region', { name: 'Selection' })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('region', { name: 'Selection' })).not.toBeInTheDocument();
  });

  it('shows the first rows only, and all of them on request', async () => {
    serve(OK(REFERENCE), OK(MANY_FLOWS));
    render(<GeoWorkspace />);
    const list = await screen.findByRole('region', { name: 'Where to look first' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(8);
    fireEvent.click(within(list).getByRole('button', { name: 'Show all 13' }));
    expect(within(list).getAllByRole('listitem')).toHaveLength(13);
    fireEvent.click(within(list).getByRole('button', { name: 'Show fewer' }));
    expect(within(list).getAllByRole('listitem')).toHaveLength(8);
  });

  it('switches view: the question, the legend, the list and the selection all follow', async () => {
    render(<GeoWorkspace />);
    const list = await screen.findByRole('region', { name: 'Where to look first' });
    fireEvent.click(within(list).getByRole('button', { name: /Norway → Iran/ }));

    fireEvent.click(tab('Login vs KYC'));
    expect(tab('Login vs KYC')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(/log in from a different country/);
    expect(screen.queryByRole('region', { name: 'Selection' })).not.toBeInTheDocument();
    const rows = within(screen.getByRole('region', { name: 'Where to look first' })).getAllByRole('button');
    expect(rows[0]).toHaveTextContent('Norway → Kenya');
    expect(rows[0]).toHaveTextContent('23 accounts');
    expect(within(screen.getByRole('list', { name: 'Map legend' })).getByText(/Registered here/)).toBeInTheDocument();
    expect(screen.getByRole('tabpanel')).toHaveTextContent('25 accounts flagged across 2 country pairs');

    fireEvent.click(tab('Jurisdictions'));
    const groups = screen.getByRole('region', { name: 'Where to look first' });
    expect(within(groups).getByText('On the FATF call-for-action list')).toBeInTheDocument();
    expect(within(groups).getByText('Largest offshore centres')).toBeInTheDocument();
    expect(screen.getByRole('tabpanel')).toHaveTextContent('1 on the call-for-action list');
    expect(within(screen.getByRole('list', { name: 'Map legend' })).getByText(/Offshore entities/)).toBeInTheDocument();
  });

  it('moves between views with the arrow keys, like the persona strip', async () => {
    render(<GeoWorkspace />);
    await screen.findByRole('region', { name: 'Where to look first' });
    fireEvent.keyDown(tab('Corridors'), { key: 'ArrowRight' });
    expect(tab('Login vs KYC')).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tab('Login vs KYC'), { key: 'End' });
    expect(tab('Jurisdictions')).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(tab('Jurisdictions'), { key: 'ArrowRight' });
    expect(tab('Corridors')).toHaveAttribute('aria-selected', 'true');
  });

  it('shows the corridor exposure by tier on the corridors view', async () => {
    render(<GeoWorkspace />);
    await screen.findByRole('region', { name: 'Where to look first' });
    const panel = screen.getByRole('tabpanel');
    expect(within(panel).getByRole('img', { name: 'Corridor volume by risk tier' })).toBeInTheDocument();
    expect(panel).toHaveTextContent('$900K');
  });

  it('keeps the sources one click away, with the as-of date visible', async () => {
    render(<GeoWorkspace />);
    await screen.findByRole('region', { name: 'Where to look first' });
    const sources = screen.getByText('Sources').closest('details')!;
    expect(sources).not.toHaveAttribute('open');
    expect(sources).toHaveTextContent('as of 2026-10-14');
    expect(sources).toHaveTextContent(/Overture Maps division_area/);
    expect(sources).toHaveTextContent(/AML engine over the seeded world/);
  });

  it('lets an analyst change the mix of layers, collapsed until asked', async () => {
    render(<GeoWorkspace />);
    await waitFor(() => expect(screen.getByLabelText(/Payment corridors/)).not.toBeDisabled());
    expect(screen.getByText('Layers').closest('details')).not.toHaveAttribute('open');
    const box = screen.getByLabelText(/Payment corridors/) as HTMLInputElement;
    expect(box.checked).toBe(true);
    expect((screen.getByLabelText(/Offshore entity centres/) as HTMLInputElement).checked).toBe(false);
    fireEvent.click(box);
    expect(box.checked).toBe(false);
    expect(screen.getByText('Layers').closest('summary')).toHaveTextContent('1 of 4 on');
  });

  it('with the reference layer down, says so with a retry, and disables every layer (flows need it to be placed)', async () => {
    serve(DOWN, OK(FLOWS));
    render(<GeoWorkspace />);
    expect(await screen.findByText(/reference layer could not be loaded \(HTTP 503\)/)).toBeInTheDocument();
    for (const name of [/FATF-listed countries/, /Offshore entity centres/, /Payment corridors/, /Login vs KYC country/]) {
      expect(screen.getByLabelText(name)).toBeDisabled();
    }
    serve(OK(REFERENCE), OK(FLOWS));
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('region', { name: 'Where to look first' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('with the flows down, keeps the jurisdictions view and disables the flow layers', async () => {
    serve(OK(REFERENCE), DOWN);
    render(<GeoWorkspace />);
    expect(await screen.findByText(/customer flows could not be loaded \(HTTP 503\)/)).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Where to look first' })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText(/FATF-listed countries/)).not.toBeDisabled());
    expect(screen.getByLabelText(/Payment corridors/)).toBeDisabled();
    fireEvent.click(tab('Jurisdictions'));
    expect(await screen.findByText('Largest offshore centres')).toBeInTheDocument();
  });

  it('shows a placeholder, not a blank panel, while the engine builds its view', () => {
    authFetch.mockImplementation(() => new Promise(() => {}));
    render(<GeoWorkspace />);
    expect(screen.getAllByTestId('geo-loading')).toHaveLength(1);
    expect(screen.getByText(/Reading customer flows from the engine/)).toBeInTheDocument();
  });

  it('shows NO_DATA, not zero, when the engine reports no corridors', async () => {
    serve(OK(REFERENCE), OK({ ...FLOWS, corridors: [], exposure: null }));
    render(<GeoWorkspace />);
    await waitFor(() => expect(within(screen.getByRole('tabpanel')).getByText('NO_DATA')).toBeInTheDocument());
  });

  it('says tiers are unavailable, rather than drawing a bar, when the engine could not rate corridors', async () => {
    serve(OK(REFERENCE), OK({ ...FLOWS, tiers_known: false, exposure: null, corridors: FLOWS.corridors.map((c) => ({ ...c, tier: null })) }));
    render(<GeoWorkspace />);
    expect(await screen.findByText(/Tiers unavailable/)).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'Corridor volume by risk tier' })).not.toBeInTheDocument();
  });
});

describe('describeSelection', () => {
  it('describes a country from the reference layer, with unmeasured values stated as such', () => {
    const view = describeSelection(FLOWS, REFERENCE, { kind: 'country', id: 'BS' });
    expect(view?.title).toBe('The Bahamas');
    expect(view?.rows).toContainEqual(['Offshore entities incorporated', '209,713']);
    expect(view?.rows).toContainEqual(['GDP per capita', '$25.2K (2020)']);
    const iran = describeSelection(FLOWS, REFERENCE, { kind: 'country', id: 'IR' });
    expect(iran?.rows).toContainEqual(['FATF list', 'Call for action']);
    expect(iran?.rows).toContainEqual(['Offshore entities incorporated', 'Not recorded']);
  });

  it('describes a corridor with country names and an unrated tier as unrated, never low', () => {
    const view = describeSelection(FLOWS, REFERENCE, { kind: 'corridor', id: 'NO>IR' });
    expect(view?.title).toBe('Norway → Iran');
    expect(view?.rows).toContainEqual(['Risk tier', 'High']);
    const unrated = { ...FLOWS, corridors: [{ ...FLOWS.corridors[0], tier: null }] };
    expect(describeSelection(unrated, REFERENCE, { kind: 'corridor', id: 'NO>IR' })?.rows).toContainEqual(['Risk tier', 'Unrated']);
  });

  it('describes a flagged country pair with its account count and examples', () => {
    const view = describeSelection(FLOWS, REFERENCE, { kind: 'mismatch', id: 'NO>KE' });
    expect(view?.title).toBe('Registered in Norway, logging in from Kenya');
    expect(view?.rows).toContainEqual(['Flagged accounts', '23']);
    expect(view?.rows).toContainEqual(['Foreign logins', '80 of 90']);
    expect(view?.rows).toContainEqual(['Examples', 'CR84920, CR11111']);
  });

  it('returns null for an unknown id, missing data, or no selection', () => {
    expect(describeSelection(FLOWS, REFERENCE, null)).toBeNull();
    expect(describeSelection(FLOWS, REFERENCE, { kind: 'corridor', id: 'nope' })).toBeNull();
    expect(describeSelection(null, REFERENCE, { kind: 'mismatch', id: 'NO>KE' })).toBeNull();
    expect(describeSelection(FLOWS, null, { kind: 'country', id: 'BS' })).toBeNull();
  });
});
