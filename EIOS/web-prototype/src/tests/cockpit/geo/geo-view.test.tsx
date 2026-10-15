import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import React from 'react';
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
import { GEO_FIXTURE } from '@/components/cockpit/geo/geo-fixture';
import { describeSelection } from '@/components/cockpit/geo/geo-format';

const respond = (status: number, body: unknown = {}) =>
  authFetch.mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });

beforeEach(() => {
  vi.unstubAllEnvs();
  authFetch.mockReset();
  respond(200, REFERENCE);
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
    expect(within(panel).getByLabelText('Message geo copilot')).toBeDisabled();
  });

  it('shows reference figures with their sources once the reference layer loads', async () => {
    render(<GeoWorkspace />);
    expect(await screen.findByText('Overture Maps division_area · as of', { exact: false })).toBeInTheDocument();
    const fatf = screen.getByRole('region', { name: 'FATF lists' });
    expect(fatf).toHaveTextContent('1 call for action');
    expect(fatf).toHaveTextContent('1 increased monitoring');
    const offshore = screen.getByRole('region', { name: 'Offshore centres' });
    expect(within(offshore).getByText('The Bahamas')).toBeInTheDocument();
    expect(within(offshore).getByText('209,713')).toBeInTheDocument();
  });

  it('says the reference layer is unavailable on a 503, shows NO_DATA, and disables the reference lenses', async () => {
    respond(503, { detail: 'reference_unavailable' });
    render(<GeoWorkspace />);
    expect(await screen.findByText(/Reference layer unavailable \(HTTP 503\)/)).toBeInTheDocument();
    expect(screen.getAllByText('NO_DATA').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByLabelText(/FATF risk areas/)).toBeDisabled();
    expect(screen.getByLabelText(/Offshore entity centres/)).toBeDisabled();
    expect(screen.getByLabelText(/Cross-border corridors/)).not.toBeDisabled();
  });

  it('keeps the customer-flow lenses togglable and labels them as fixture', async () => {
    render(<GeoWorkspace />);
    await waitFor(() => expect(screen.getByLabelText(/FATF risk areas/)).not.toBeDisabled());
    const box = screen.getByLabelText(/Cross-border corridors/) as HTMLInputElement;
    expect(box.checked).toBe(true);
    fireEvent.click(box);
    expect(box.checked).toBe(false);
    expect(screen.getAllByText('Fixture').length).toBeGreaterThanOrEqual(2);
  });

  it('shows NO_DATA, not zero, for corridor volume when the flows are empty', async () => {
    render(<GeoWorkspace evidence={{ ...GEO_FIXTURE, corridors: [] }} />);
    expect(await screen.findAllByText('NO_DATA')).not.toHaveLength(0);
  });
});

describe('describeSelection', () => {
  it('describes a country from the reference layer, with unmeasured values stated as such', () => {
    const view = describeSelection(GEO_FIXTURE, REFERENCE, { kind: 'country', id: 'BS' });
    expect(view?.title).toBe('The Bahamas');
    expect(view?.rows).toContainEqual(['Offshore entities incorporated', '209,713']);
    expect(view?.rows).toContainEqual(['GDP per capita', '$25.2K (2020)']);
    const iran = describeSelection(GEO_FIXTURE, REFERENCE, { kind: 'country', id: 'IR' });
    expect(iran?.rows).toContainEqual(['FATF list', 'Call for action']);
    expect(iran?.rows).toContainEqual(['Offshore entities incorporated', 'Not recorded']);
  });

  it('describes flows from the fixture and returns null for an unknown id or no reference', () => {
    expect(describeSelection(GEO_FIXTURE, null, null)).toBeNull();
    expect(describeSelection(GEO_FIXTURE, REFERENCE, { kind: 'corridor', id: 'C-CY-PA' })?.title).toBe('Cyprus → Panama');
    expect(describeSelection(GEO_FIXTURE, REFERENCE, { kind: 'mismatch', id: 'CR84920' })?.rows[1]).toEqual(['IP country', 'Nigeria']);
    expect(describeSelection(GEO_FIXTURE, REFERENCE, { kind: 'corridor', id: 'nope' })).toBeNull();
    expect(describeSelection(GEO_FIXTURE, null, { kind: 'country', id: 'BS' })).toBeNull();
  });
});
