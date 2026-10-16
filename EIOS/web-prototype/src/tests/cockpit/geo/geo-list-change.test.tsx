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
  const panel = (state: Parameters<typeof GeoListChangePanel>[0]['state'] = { status: 'ready', data: CHANGE }, onSelect = vi.fn(), onClose = vi.fn()) =>
    render(<GeoListChangePanel state={state} onClose={onClose} onSelect={onSelect} />);

  it('is one table, one row per country, the most exposed first, saying what happened to each', () => {
    panel();
    const rows = screen.getAllByRole('row').slice(1);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('Nigeria');
    expect(rows[0]).toHaveTextContent('Removed · was EU high-risk');
    expect(rows[0]).toHaveTextContent('330');
    expect(rows[0]).toHaveTextContent('100.0%');
    expect(rows[1]).toHaveTextContent('British Virgin Islands');
    expect(rows[1]).toHaveTextContent('Added · EU high-risk');
    expect(rows[1]).toHaveTextContent('16');
    expect(rows[1]).toHaveTextContent('—');
  });

  it('names the edition change once, and the duty that ends when a country leaves a list', () => {
    panel();
    expect(screen.getByText('Compared with EU list before January 2026.')).toBeInTheDocument();
    expect(screen.getByText(/the activity below continues|the activity continues/)).toBeInTheDocument();
  });

  it('keeps what the book does in a country behind its row, and says what it cannot know', () => {
    panel();
    expect(screen.queryByText('Shared exit here: GW-NG-X00')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Nigeria/ }));
    expect(screen.getByText('Shared exit here: GW-NG-X00')).toBeInTheDocument();
    expect(screen.getByText(/266 registered there/)).toBeInTheDocument();
    expect(screen.getByText(/Links not available: the graph could not be reached/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /British Virgin Islands/ }));
    expect(screen.getByText(/16 pay through it \(\$131\.1K\)/)).toBeInTheDocument();
  });

  it('picks the country on the map when its row is opened, and closes the facts again', () => {
    const onSelect = vi.fn();
    panel({ status: 'ready', data: CHANGE }, onSelect);
    const row = screen.getByRole('button', { name: /Nigeria/ });
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith({ kind: 'country', id: 'NG' });
    expect(row).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(row);
    expect(row).toHaveAttribute('aria-expanded', 'false');
  });

  it('says the graph links are unavailable instead of showing zero', () => {
    panel();
    fireEvent.click(screen.getByText('Sources and method'));
    expect(screen.getByText(/Links unavailable: warehouse unreachable/)).toBeInTheDocument();
  });

  it('shows the load state and a failure with its status, and closes', () => {
    const onClose = vi.fn();
    const { rerender } = render(<GeoListChangePanel state={{ status: 'loading' }} onClose={onClose} onSelect={vi.fn()} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    rerender(<GeoListChangePanel state={{ status: 'error', httpStatus: 503, reload: vi.fn() }} onClose={onClose} onSelect={vi.fn()} />);
    expect(screen.getByText(/503/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalled();
  });
});
