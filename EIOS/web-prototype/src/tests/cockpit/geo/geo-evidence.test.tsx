import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { GeoEvidence } from '@/components/cockpit/geo/geo-evidence';
import { bundleIdOf } from '@/lib/server/normalize';

const ID = 'a'.repeat(64);

function reply(status: number, body: unknown) {
  authFetch.mockResolvedValue({ ok: status < 400, status, json: async () => body });
}

function replay() {
  render(<GeoEvidence bundleId={ID} />);
  fireEvent.click(screen.getByText('Replay evidence'));
}

beforeEach(() => {
  authFetch.mockReset();
});

describe('sealed evidence', () => {
  it('shows the seal and replays it through the backend', async () => {
    reply(200, { intact: true, equal: true, figures: 7, differing: 0, calls: [{}, {}] });
    replay();
    expect(await screen.findByTestId('geo-evidence-result')).toHaveTextContent(
      'all 7 figures from 2 sealed calls come back the same',
    );
    expect(authFetch.mock.calls[0][0]).toBe(`/api/cockpit/evidence/${ID}/replay`);
    expect(screen.getByTestId('geo-evidence')).toHaveTextContent('sha256 aaaaaaaaaaaa');
  });

  it('says how many figures moved since sealing, never that it is equal', async () => {
    reply(200, { intact: true, equal: false, figures: 7, differing: 2, calls: [{}] });
    replay();
    expect(await screen.findByTestId('geo-evidence-result')).toHaveTextContent('2 of 7 figures differ');
  });

  it('says an altered bundle cannot be relied on', async () => {
    reply(200, { intact: false, equal: false, calls: [] });
    replay();
    expect(await screen.findByTestId('geo-evidence-result')).toHaveTextContent('no longer matches its hash');
  });

  it.each([[503, { detail: 'offline' }], [200, {}], [200, { intact: true, equal: true, calls: [] }]])(
    'treats an outage or a reply without its counts as nothing compared (%s)',
    async (status, body) => {
      reply(status, body);
      replay();
      expect(await screen.findByRole('alert')).toHaveTextContent('Nothing was compared');
    },
  );
});

describe('bundle ids', () => {
  it('accepts only 64 lowercase hex characters', () => {
    expect(bundleIdOf(ID)).toBe(ID);
    expect(bundleIdOf('A'.repeat(64))).toBeUndefined();
    expect(bundleIdOf('../evil')).toBeUndefined();
    expect(bundleIdOf(42)).toBeUndefined();
  });
});
