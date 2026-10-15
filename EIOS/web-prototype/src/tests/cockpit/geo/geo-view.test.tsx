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

  it('explains the marks with a legend', () => {
    render(<GeoWorkspace />);
    const legend = screen.getByRole('list', { name: 'Map legend' });
    expect(within(legend).getByText('FATF call for action')).toBeInTheDocument();
    expect(within(legend).getByText(/Offshore entities/)).toBeInTheDocument();
  });

  it('states the copilot is not connected and never offers a live answer', () => {
    render(<GeoWorkspace />);
    const panel = screen.getByRole('complementary', { name: 'Geo copilot' });
    expect(within(panel).getByText('Not connected')).toBeInTheDocument();
    expect(within(panel).queryByLabelText('Message geo copilot')).not.toBeInTheDocument(); // collapsed by default
    fireEvent.click(within(panel).getByRole('button', { name: /Geo copilot/ }));
    expect(within(panel).getByLabelText('Message geo copilot')).toBeDisabled();
  });

  it('shows reference and engine figures with their sources once both load', async () => {
    render(<GeoWorkspace />);
    expect(await screen.findByText(/AML engine over the seeded world/)).toBeInTheDocument();
    expect(screen.getByText(/Overture Maps division_area/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'FATF lists' })).toHaveTextContent('1 call for action');
    const top = screen.getByRole('region', { name: 'Top corridors' });
    expect(within(top).getByText('NO → IR')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Corridor volume by risk tier' })).toHaveTextContent('25');
  });

  it('with the reference layer down, disables every lens (flows need it to be placed) and says so', async () => {
    serve(DOWN, OK(FLOWS));
    render(<GeoWorkspace />);
    expect(await screen.findByText(/Reference layer unavailable \(HTTP 503\)/)).toBeInTheDocument();
    for (const name of [/FATF risk areas/, /Offshore entity centres/, /Cross-border corridors/, /IP vs KYC country/]) {
      expect(screen.getByLabelText(name)).toBeDisabled();
    }
  });

  it('with the flows down, keeps the reference lenses and disables the flow lenses', async () => {
    serve(OK(REFERENCE), DOWN);
    render(<GeoWorkspace />);
    expect(await screen.findByText(/Customer flows unavailable \(HTTP 503\)/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText(/FATF risk areas/)).not.toBeDisabled());
    expect(screen.getByLabelText(/Cross-border corridors/)).toBeDisabled();
    expect(within(screen.getByRole('region', { name: 'Top corridors' })).getByText('NO_DATA')).toBeInTheDocument();
  });

  it('lets an analyst turn each evidence lens off and on', async () => {
    render(<GeoWorkspace />);
    await waitFor(() => expect(screen.getByLabelText(/Cross-border corridors/)).not.toBeDisabled());
    const box = screen.getByLabelText(/Cross-border corridors/) as HTMLInputElement;
    expect(box.checked).toBe(true);
    fireEvent.click(box);
    expect(box.checked).toBe(false);
  });

  it('shows NO_DATA, not zero, for corridor volume when the engine reports no corridors', async () => {
    serve(OK(REFERENCE), OK({ ...FLOWS, corridors: [], exposure: null }));
    render(<GeoWorkspace />);
    const region = await screen.findByRole('region', { name: 'Corridor volume by risk tier' });
    await waitFor(() => expect(within(region).getByText('NO_DATA')).toBeInTheDocument());
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
