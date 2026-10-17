import { describe, it, expect } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { GeoLegend } from '@/components/cockpit/geo/geo-legend';
import { FLOWS } from './flows-fixture';

const VISIBLE = new Set<'risk' | 'corridors'>(['risk', 'corridors']);

describe('the legend on a narrow map', () => {
  it('is a key you open, not one that is dropped: the colours are still explained', () => {
    render(<GeoLegend visible={VISIBLE} flows={FLOWS} />);
    const toggle = screen.getByRole('button', { name: /key/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('list', { name: 'Map legend' }).className).toMatch(/\bhidden\b/);
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('list', { name: 'Map legend' }).className).not.toMatch(/\bhidden\b/);
  });

  it('keeps what is drawn in view beside the toggle, so the count is never hidden', () => {
    render(<GeoLegend visible={VISIBLE} flows={FLOWS} />);
    expect(screen.getByRole('button', { name: /key/i })).toHaveTextContent(/Showing 3 of 3 corridors/);
  });

  it('puts the long notes behind the toggle too, so a closed key is one line', () => {
    render(<GeoLegend visible={new Set(['offshore'])} flows={FLOWS} />);
    expect(screen.getByText(/ICIJ Offshore/).closest('[data-legend-notes]')?.className).toMatch(/\bhidden\b/);
  });
});
