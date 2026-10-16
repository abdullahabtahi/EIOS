import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import React from 'react';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';
import { leadsFor } from '@/components/cockpit/geo/geo-leads';
import { GeoLeadList } from '@/components/cockpit/geo/geo-lead-list';
import { GeoSide } from '@/components/cockpit/geo/geo-side';
import type { GeoFlows } from '@/components/cockpit/geo/geo-types';

const BACK = { origin: 'IR', destination: 'NO', volume_usd: 50_000, accounts: 2, events: 5, tier: 'high' as const };
const TWO_WAY: GeoFlows = { ...FLOWS, corridors: [...FLOWS.corridors, BACK] };
const leads = (flows: GeoFlows) => leadsFor('corridors', flows, REFERENCE)!;

describe('the corridor list', () => {
  it('lists the two directions of a pair as one row, led by the bigger, and says it runs both ways', () => {
    const rows = leads(TWO_WAY);
    expect(rows).toHaveLength(FLOWS.corridors.length);
    const pair = rows.find((r) => r.selection.id === 'NO>IR')!;
    expect(pair.title).toBe('Norway ↔ Iran');
    expect(pair.detail).toContain('$50K back');
    expect(rows.some((r) => r.selection.id === 'IR>NO')).toBe(false);
    expect(leads(FLOWS).find((r) => r.selection.id === 'NO>IR')!.title).toBe('Norway → Iran');
  });

  it('groups by tier so no row has to repeat it, in the order high, medium, other', () => {
    expect(leads(FLOWS).map((r) => r.group)).toEqual(['High risk', 'Medium risk', 'Other corridors']);
  });

  it('gives each row its volume as a share of the largest, for a bar, without inventing a number to show', () => {
    const shares = leads(FLOWS).map((r) => r.share);
    expect(shares[0]).toBe(1);
    expect(shares.every((s) => s !== undefined && s > 0 && s <= 1)).toBe(true);
  });

  it('counts an unrated corridor as other, never as elevated', () => {
    const unrated = { ...FLOWS, corridors: FLOWS.corridors.map((c) => ({ ...c, tier: null })) };
    expect(new Set(leads(unrated).map((r) => r.group))).toEqual(new Set(['Other corridors']));
  });
});

describe('GeoLeadList', () => {
  const many = (n: number) =>
    Array.from({ length: n }, (_, i) => ({
      key: `c${i}`,
      selection: { kind: 'corridor', id: `A${i}>B${i}` } as const,
      title: `Country ${i} → Place ${i}`,
      detail: '$1K · 1 account',
      tier: null,
      group: 'Other corridors',
      share: 0.5,
    }));

  it('moves between rows with the arrow keys and j and k, and Home and End', () => {
    render(<GeoLeadList leads={many(5)} selected={null} onSelect={vi.fn()} />);
    const rows = screen.getAllByRole('button', { name: /Country/ });
    rows[0].focus();
    fireEvent.keyDown(rows[0], { key: 'ArrowDown' });
    expect(rows[1]).toHaveFocus();
    fireEvent.keyDown(rows[1], { key: 'j' });
    expect(rows[2]).toHaveFocus();
    fireEvent.keyDown(rows[2], { key: 'k' });
    expect(rows[1]).toHaveFocus();
    fireEvent.keyDown(rows[1], { key: 'End' });
    expect(rows[4]).toHaveFocus();
    fireEvent.keyDown(rows[4], { key: 'Home' });
    expect(rows[0]).toHaveFocus();
    fireEvent.keyDown(rows[0], { key: 'ArrowUp' });
    expect(rows[0]).toHaveFocus();
  });

  it('offers a filter only when the list is longer than what it shows first, and narrows by what is typed', () => {
    const { rerender } = render(<GeoLeadList leads={many(5)} selected={null} onSelect={vi.fn()} />);
    expect(screen.queryByRole('searchbox')).toBeNull();
    rerender(<GeoLeadList leads={many(20)} selected={null} onSelect={vi.fn()} />);
    const box = screen.getByRole('searchbox', { name: 'Filter the list' });
    fireEvent.change(box, { target: { value: 'place 13' } });
    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(1);
    expect(items[0]).toHaveTextContent('Country 13');
    fireEvent.change(box, { target: { value: 'zzz' } });
    expect(screen.getByText(/Nothing matches/)).toBeInTheDocument();
  });

  it('clears the filter with Escape, and keeps that Escape to itself', () => {
    const onEsc = vi.fn();
    window.addEventListener('keydown', onEsc);
    render(<GeoLeadList leads={many(20)} selected={null} onSelect={vi.fn()} />);
    const box = screen.getByRole('searchbox', { name: 'Filter the list' });
    fireEvent.change(box, { target: { value: 'country 1' } });
    fireEvent.keyDown(box, { key: 'Escape' });
    expect(box).toHaveValue('');
    expect(onEsc).not.toHaveBeenCalled();
    window.removeEventListener('keydown', onEsc);
  });

  it('draws a bar per row from its share, hidden from assistive tech', () => {
    render(<GeoLeadList leads={many(2)} selected={null} onSelect={vi.fn()} />);
    const bar = within(screen.getAllByRole('listitem')[0]).getByTestId('lead-bar');
    expect(bar).toHaveAttribute('aria-hidden', 'true');
    expect(bar.style.width).toBe('50%');
  });
});

describe('GeoSide tabs', () => {
  const side = (onPanel = vi.fn(), panel: 'explore' | 'ask' = 'explore') =>
    render(<GeoSide panel={panel} onPanel={onPanel} explore={<p>explore body</p>} ask={<p>ask body</p>} />);

  it('keeps only the open tab in the tab order and names the panel each one controls', () => {
    side();
    const explore = screen.getByRole('tab', { name: 'Explore' });
    const ask = screen.getByRole('tab', { name: 'Ask' });
    expect(explore).toHaveAttribute('tabindex', '0');
    expect(ask).toHaveAttribute('tabindex', '-1');
    for (const t of [explore, ask]) expect(document.getElementById(t.getAttribute('aria-controls')!)).not.toBeNull();
  });

  it('moves between tabs with the arrow keys, Home and End', () => {
    const onPanel = vi.fn();
    side(onPanel);
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Explore' }), { key: 'ArrowRight' });
    expect(onPanel).toHaveBeenLastCalledWith('ask');
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Explore' }), { key: 'End' });
    expect(onPanel).toHaveBeenLastCalledWith('ask');
  });

  it('wraps from the last tab back to the first', () => {
    const onPanel = vi.fn();
    side(onPanel, 'ask');
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Ask' }), { key: 'ArrowRight' });
    expect(onPanel).toHaveBeenLastCalledWith('explore');
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Ask' }), { key: 'ArrowLeft' });
    expect(onPanel).toHaveBeenLastCalledWith('explore');
  });
});
