import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { GeoListChangePanel } from '@/components/cockpit/geo/geo-list-change';
import type { GeoListChange, ListChangeCountry } from '@/components/cockpit/geo/geo-types';

const country = (over: Partial<ListChangeCountry>): ListChangeCountry => ({
  iso2: 'XX',
  name: 'Nowhere',
  before: null,
  after: null,
  registered_accounts: 0,
  login_accounts: 0,
  sessions: 0,
  payment_accounts: 0,
  payment_volume_usd: 0,
  shared_exits: [],
  exposed_accounts: 0,
  linked_accounts: 0,
  ...over,
});
const empty = { countries: [], exposed_accounts: 0, sessions: 0, payment_volume_usd: 0, session_shares: null, payment_shares: null };

const CHANGE: GeoListChange = {
  list_id: 'eu',
  as_of: '2026-10-14T08:00:00+00:00',
  source: 'AML engine',
  before: { label: 'EU list before January 2026', in_force: 'until 2026-01-28', source: 'derived' },
  after: { label: 'EU list as amended to 2026/83', in_force: 'from 2026-01-29', source: 'European Commission' },
  added: {
    countries: [country({ iso2: 'VG', name: 'British Virgin Islands', after: 'eu_high_risk', payment_accounts: 16, payment_volume_usd: 131082.18, exposed_accounts: 16, linked_accounts: 4 })],
    exposed_accounts: 16,
    sessions: 0,
    payment_volume_usd: 131082.18,
    session_shares: null,
    payment_shares: { VG: 100 },
  },
  removed: {
    countries: [
      country({ iso2: 'NG', name: 'Nigeria', before: 'eu_high_risk', registered_accounts: 266, login_accounts: 323, sessions: 2612, shared_exits: ['GW-NG-X00'], exposed_accounts: 330, linked_accounts: null }),
    ],
    exposed_accounts: 330,
    sessions: 2612,
    payment_volume_usd: 0,
    session_shares: { NG: 100 },
    payment_shares: null,
  },
  relisted: empty,
  graph: { source: null, seconds: null, error: 'warehouse unreachable' },
};

describe('what a list change does to the book', () => {
  it('names each country, what the book does there and the exits located there', () => {
    render(<GeoListChangePanel listId="eu" state={{ status: 'ready', data: CHANGE }} onList={vi.fn()} onClose={vi.fn()} onSelect={vi.fn()} />);
    expect(screen.getByText(/Added to the list · 16 accounts touched/)).toBeInTheDocument();
    expect(screen.getByText(/16 pay through it \(\$131\.1K\)/)).toBeInTheDocument();
    expect(screen.getByText('Shared exit here: GW-NG-X00')).toBeInTheDocument();
    expect(screen.getByText(/the activity below continues/)).toBeInTheDocument();
    expect(screen.getByText('EU high-risk → not listed')).toBeInTheDocument();
  });

  it('says the graph links are unavailable instead of showing zero', () => {
    render(<GeoListChangePanel listId="eu" state={{ status: 'ready', data: CHANGE }} onList={vi.fn()} onClose={vi.fn()} onSelect={vi.fn()} />);
    expect(screen.getByText(/Links not available: the graph could not be reached/)).toBeInTheDocument();
    expect(screen.getByText(/Links unavailable: warehouse unreachable/)).toBeInTheDocument();
  });

  it('selects a country on the map and switches between the two lists', () => {
    const onSelect = vi.fn();
    const onList = vi.fn();
    render(<GeoListChangePanel listId="eu" state={{ status: 'ready', data: CHANGE }} onList={onList} onClose={vi.fn()} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Nigeria'));
    expect(onSelect).toHaveBeenCalledWith({ kind: 'country', id: 'NG' });
    fireEvent.click(screen.getByRole('radio', { name: 'FATF, June 2026 plenary' }));
    expect(onList).toHaveBeenCalledWith('fatf');
  });

  it('shows the load state and a failure with its status', () => {
    const { rerender } = render(<GeoListChangePanel listId="fatf" state={{ status: 'loading' }} onList={vi.fn()} onClose={vi.fn()} onSelect={vi.fn()} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    rerender(<GeoListChangePanel listId="fatf" state={{ status: 'error', httpStatus: 503, reload: vi.fn() }} onList={vi.fn()} onClose={vi.fn()} onSelect={vi.fn()} />);
    expect(screen.getByText(/503/)).toBeInTheDocument();
  });
});
