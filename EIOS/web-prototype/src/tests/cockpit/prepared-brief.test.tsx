import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { PreparedBriefCard } from '@/components/cockpit/shell/prepared-brief-card';
import { normalizeBrief } from '@/lib/server/normalize';

const BODY = {
  entity_id: 'CR84920',
  prepared_at: '2026-10-16T14:05:00+00:00',
  expires_at: '2026-10-16T15:05:00+00:00',
  stale: false,
  response: 'The discrepancy is 16x.',
  provenance_citations: [
    { metric_id: 'aml.dossier:CR84920:discrepancy_multiplier', formatted_value: '16x', source: 'aml engine', unit: 'x', raw_value: 16, data_origin: 'engine', as_of: '2026-10-16T14:00:00+00:00' },
  ],
  sources: [],
};

function reply(status: number, body: unknown) {
  authFetch.mockResolvedValue({ ok: status < 400, status, json: async () => body });
}

beforeEach(() => authFetch.mockReset());

describe('prepared brief card', () => {
  it('shows the brief with when it was prepared, and reads it from the proxy once', async () => {
    reply(200, normalizeBrief(BODY));
    render(<PreparedBriefCard entityId="CR84920" />);
    expect(await screen.findByText(/prepared at 14:05 UTC/)).toBeInTheDocument();
    expect(screen.getByText(/The discrepancy is 16x/)).toBeInTheDocument();
    expect(authFetch.mock.calls[0][0]).toBe('/api/cockpit/ambient/briefs/CR84920');
    expect(authFetch).toHaveBeenCalledTimes(1);
  });

  it('says a stale brief is older than its time to live', async () => {
    reply(200, normalizeBrief({ ...BODY, stale: true }));
    render(<PreparedBriefCard entityId="CR84920" />);
    expect(await screen.findByText(/older than its time to live/)).toBeInTheDocument();
  });

  it('says plainly when no brief was prepared, and shows nothing in its place', async () => {
    reply(404, { detail: 'no brief has been prepared for this alert' });
    render(<PreparedBriefCard entityId="CR84920" />);
    expect(await screen.findByText(/No brief was prepared for this alert/)).toBeInTheDocument();
    expect(screen.queryByText(/prepared at/)).toBeNull();
  });

  it('treats a reply that is not a brief as not loaded, never as an empty card', async () => {
    reply(200, {});
    render(<PreparedBriefCard entityId="CR84920" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded (HTTP 502)');
  });

  it('reports an outage as not loaded, never as an empty brief', async () => {
    reply(503, { detail: 'offline' });
    render(<PreparedBriefCard entityId="CR84920" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded (HTTP 503)');
  });
});

describe('normalizeBrief', () => {
  it('keeps the figures as cited metrics', () => {
    const brief = normalizeBrief(BODY);
    expect(brief?.citedMetrics[0].formattedValue).toBe('16x');
    expect(brief?.stale).toBe(false);
  });

  it.each([null, {}, { ...BODY, response: '' }, { ...BODY, entity_id: '' }, { ...BODY, prepared_at: 'never' }])(
    'drops a body that is not a brief (%j)',
    (raw) => {
      expect(normalizeBrief(raw)).toBeUndefined();
    },
  );
});
