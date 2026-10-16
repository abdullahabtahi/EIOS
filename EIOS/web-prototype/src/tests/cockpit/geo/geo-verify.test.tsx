import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import type { MetricProvenance } from '@/components/cockpit/state/cockpit-types';

const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { GeoVerify } from '@/components/cockpit/geo/geo-verify';

const figure = (metricId: string, rawValue: number | string): MetricProvenance => ({
  metricId,
  name: metricId,
  rawValue,
  formattedValue: String(rawValue),
  semanticDefinitionVersion: '',
  asOfTimestamp: '2026-10-14T08:00:00Z',
  originEngine: 'engine',
  stewardRole: '',
  citation: { sourceSystem: '', queryReference: '', retrievedAt: '' } as unknown as MetricProvenance['citation'],
  isCached: false,
});
const FIGURES = [figure('geo.exit:GW-NG-X00:flagged_accounts', 22), figure('geo.corridor:ID>MM:volume_usd', 45308.04)];

function reply(status: number, body: unknown) {
  authFetch.mockResolvedValue({ ok: status < 400, status, json: async () => body });
}

beforeEach(() => {
  authFetch.mockReset();
});

describe('verify figures', () => {
  it('sends every numeric figure and says when all are derived again unchanged', async () => {
    reply(200, {
      checked: 2,
      matched: 2,
      rows: FIGURES.map((f) => ({ fact_id: f.metricId, match: true, error: null })),
    });
    render(<GeoVerify figures={FIGURES} role="geospatial" />);
    fireEvent.click(screen.getByText('Verify figures'));
    expect(await screen.findByTestId('geo-verify-result')).toHaveTextContent('all 2 figures match');
    const body = JSON.parse(authFetch.mock.calls[0][1].body);
    expect(body).toEqual({
      role: 'geospatial',
      figures: [
        { fact_id: 'geo.exit:GW-NG-X00:flagged_accounts', value: 22 },
        { fact_id: 'geo.corridor:ID>MM:volume_usd', value: 45308.04 },
      ],
    });
  });

  it('names the figures that were not verified', async () => {
    reply(200, {
      checked: 2,
      matched: 1,
      rows: [
        { fact_id: 'geo.exit:GW-NG-X00:flagged_accounts', match: true, error: null },
        { fact_id: 'geo.corridor:ID>MM:volume_usd', match: false, error: 'NOT_FOUND' },
      ],
    });
    render(<GeoVerify figures={FIGURES} role="geospatial" />);
    fireEvent.click(screen.getByText('Verify figures'));
    expect(await screen.findByTestId('geo-verify-result')).toHaveTextContent('1 of 2 match. Not verified: volume_usd.');
  });

  it('says the check could not run, never that it passed', async () => {
    reply(503, { detail: 'offline' });
    render(<GeoVerify figures={FIGURES} role="geospatial" />);
    fireEvent.click(screen.getByText('Verify figures'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Nothing was verified');
  });

  it.each([
    [{}],
    [{ checked: 2, matched: 2 }],
    [{ checked: 0, matched: 0, rows: [] }],
    [{ checked: 2, matched: 2, rows: [] }],
  ])('treats a reply without its counts and rows as a failed check, not a pass (%j)', async (body) => {
    reply(200, body);
    render(<GeoVerify figures={FIGURES} role="geospatial" />);
    fireEvent.click(screen.getByText('Verify figures'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Nothing was verified');
  });

  it('offers nothing when the answer has no figure', () => {
    const { container } = render(<GeoVerify figures={[figure('x', 'n/a')]} role="geospatial" />);
    expect(container).toBeEmptyDOMElement();
  });
});
