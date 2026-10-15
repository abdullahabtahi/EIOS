import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { GeoAddressCheck } from '@/components/cockpit/geo/geo-address-check';
import type { GeoAddress } from '@/components/cockpit/geo/geo-types';

const SOURCES = [
  { name: 'IPinfo Lite', as_of: '2026-10-15' },
  { name: 'Tor Project bulk exit list', as_of: '2026-10-15' },
];
const TOR: GeoAddress = {
  address: '171.25.193.25', version: 4, scope: 'public',
  country: { iso2: 'SE', name: 'Sweden' },
  network: { asn: 198093, name: 'Foreningen for digitala fri- och rattigheter', domain: 'dfri.net' },
  verdict: 'tor_exit', lists: [{ list: 'tor_exit', detail: '' }], uncovered: [], sources: SOURCES,
};
const reply = (status: number, body?: unknown) => authFetch.mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body ?? {} });
const check = (value: string) => {
  fireEvent.change(screen.getByLabelText('IP address'), { target: { value } });
  fireEvent.click(screen.getByRole('button', { name: 'Check' }));
};

beforeEach(() => authFetch.mockReset());

describe('address check', () => {
  it('has a labelled field and cannot be submitted empty', () => {
    render(<GeoAddressCheck />);
    expect(screen.getByRole('button', { name: 'Check' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('IP address'), { target: { value: '  ' } });
    expect(screen.getByRole('button', { name: 'Check' })).toBeDisabled();
  });

  it('posts the address in the body, never in the URL', async () => {
    reply(200, TOR);
    render(<GeoAddressCheck />);
    check(' 171.25.193.25 ');
    await screen.findByText('On the Tor exit list');
    const [url, init] = authFetch.mock.calls[0];
    expect(url).toBe('/api/cockpit/geo/address');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({ address: '171.25.193.25' });
    expect(String(url)).not.toContain('171.25');
  });

  it('shows the country, the network, every matching list and where the data comes from', async () => {
    reply(200, { ...TOR, lists: [{ list: 'tor_exit', detail: '' }, { list: 'cloud', detail: 'Amazon Web Services, EC2, us-east-1' }] });
    render(<GeoAddressCheck />);
    check('171.25.193.25');
    await screen.findByText('On the Tor exit list');
    expect(screen.getByText('Sweden')).toBeInTheDocument();
    expect(screen.getByText(/AS198093/)).toHaveTextContent('Foreningen for digitala fri- och rattigheter');
    expect(screen.getByText('Tor exit relay')).toBeInTheDocument();
    expect(screen.getByText('Cloud range: Amazon Web Services, EC2, us-east-1')).toBeInTheDocument();
    expect(screen.getByText('IPinfo Lite · as of 2026-10-15')).toBeInTheDocument();
    expect(screen.getByText('Tor Project bulk exit list · as of 2026-10-15')).toBeInTheDocument();
  });

  it('credits IPinfo with a link, as its licence asks', async () => {
    reply(200, TOR);
    render(<GeoAddressCheck />);
    check('171.25.193.25');
    const link = await screen.findByRole('link', { name: 'IPinfo' });
    expect(link).toHaveAttribute('href', 'https://ipinfo.io');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('says "not on any list we hold" and that this is not a clean bill', async () => {
    reply(200, { ...TOR, verdict: 'none_listed', lists: [] });
    render(<GeoAddressCheck />);
    check('171.25.193.25');
    expect(await screen.findByText('Not on any list we hold')).toBeInTheDocument();
    expect(screen.getByText(/does not mean the address is clean/i)).toBeInTheDocument();
  });

  it('names a list that holds nothing of this address family, so it cannot be read as ruling the address out', async () => {
    reply(200, { ...TOR, address: '2606:4700::1', version: 6, verdict: 'none_listed', lists: [], uncovered: ['tor_exit', 'vpn', 'datacenter'] });
    render(<GeoAddressCheck />);
    check('2606:4700::1');
    expect(await screen.findByText(/Tor, VPN and datacenter lists hold no IPv6 networks/)).toBeInTheDocument();
  });

  it('does not look up a private address and says why', async () => {
    reply(200, { address: '10.0.0.1', version: 4, scope: 'private', country: null, network: null, verdict: 'not_public', lists: [], uncovered: [], sources: SOURCES });
    render(<GeoAddressCheck />);
    check('10.0.0.1');
    expect(await screen.findByText(/private address/i)).toBeInTheDocument();
    expect(screen.queryByText('Country')).not.toBeInTheDocument();
  });

  it('says "Not in the database" for an address with no country, never a guess', async () => {
    reply(200, { ...TOR, country: null, network: null, verdict: 'none_listed', lists: [] });
    render(<GeoAddressCheck />);
    check('171.25.193.25');
    expect(await screen.findByText('Not in the database')).toBeInTheDocument();
  });

  it('reads the country as where the address is registered, not where the person is', async () => {
    reply(200, TOR);
    render(<GeoAddressCheck />);
    check('171.25.193.25');
    expect(await screen.findByText(/where the address is registered/i)).toBeInTheDocument();
  });

  it('explains a missing snapshot and a malformed address in words', async () => {
    reply(503, { detail: 'address_check_unavailable' });
    render(<GeoAddressCheck />);
    check('171.25.193.25');
    expect(await screen.findByRole('alert')).toHaveTextContent(/no network data loaded/i);
    reply(422, { detail: 'not_an_ip_address' });
    check('nope');
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/not an IP address/i));
  });

  it('can put the country on the map only when the map knows that country', async () => {
    reply(200, TOR);
    const onShowCountry = vi.fn();
    const { rerender } = render(<GeoAddressCheck onShowCountry={onShowCountry} knownCountries={new Set(['SE'])} />);
    check('171.25.193.25');
    fireEvent.click(await screen.findByRole('button', { name: 'Show Sweden on the map' }));
    expect(onShowCountry).toHaveBeenCalledWith('SE');
    rerender(<GeoAddressCheck onShowCountry={onShowCountry} knownCountries={new Set(['NO'])} />);
    expect(screen.queryByRole('button', { name: 'Show Sweden on the map' })).not.toBeInTheDocument();
  });
});
