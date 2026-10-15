import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import React from 'react';
import { REFERENCE } from './reference-fixture';
import { FLOWS } from './flows-fixture';

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

const NORWAY = {
  address: '5.5.5.5', version: 4, scope: 'public', country: { iso2: 'NO', name: 'Norway' }, network: { asn: 1, name: 'Example Net', domain: 'example.net' },
  verdict: 'none_listed', lists: [], uncovered: [], sources: [{ name: 'IPinfo Lite', as_of: '2026-10-15' }],
};

beforeEach(() => {
  window.history.replaceState(null, '', '/');
  authFetch.mockReset();
  authFetch.mockImplementation(async (url: string) => ({
    ok: true,
    status: 200,
    json: async () => (url.includes('/geo/address') ? NORWAY : url.includes('/geo/flows') ? FLOWS : REFERENCE),
  }));
});

describe('address check in the Login vs KYC view', () => {
  it('is one closed line in the Login view and absent from the other views', async () => {
    render(<GeoWorkspace />);
    await screen.findByRole('region', { name: 'Where to look first' });
    expect(screen.queryByText('Check an IP address')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Login vs KYC' }));
    const summary = screen.getByText('Check an IP address');
    expect(summary.closest('details')).not.toHaveAttribute('open');
  });

  it('checks an address and puts its country on the map', async () => {
    render(<GeoWorkspace />);
    await screen.findByRole('region', { name: 'Where to look first' });
    fireEvent.click(screen.getByRole('tab', { name: 'Login vs KYC' }));
    fireEvent.click(screen.getByText('Check an IP address'));
    fireEvent.change(screen.getByLabelText('IP address'), { target: { value: '5.5.5.5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Show Norway on the map' }));
    expect(window.location.search).toContain('sel=country%3ANO');
    expect(within(screen.getByRole('region', { name: 'Selection' })).getByText('Norway')).toBeInTheDocument();
  });
});
