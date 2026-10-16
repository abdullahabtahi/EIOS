/* eslint-disable @typescript-eslint/no-explicit-any */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET as getShelf } from '@/app/api/cockpit/shelf/route';
import { GET as getWorkstation } from '@/app/api/cockpit/workstations/[role]/route';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const req = (path: string) => new Request(`http://localhost:3000${path}`) as any;

describe('shelf proxy and the shelf-less workstation call', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it('relays the shelf, never cacheable', async () => {
    fetchMock.mockResolvedValue(json(200, { governed_action_shelf: { staged_count: 0, actions: [] } }));
    const res = await getShelf(req('/api/cockpit/shelf'));
    expect(res.status).toBe(200);
    expect(res.headers.get('Cache-Control')).toBe('no-store');
    expect((await res.json()).stagedActionCards).toEqual([]);
  });

  it('answers 503 when the backend is down, never an invented shelf', async () => {
    fetchMock.mockRejectedValue(new TypeError('down'));
    expect((await getShelf(req('/api/cockpit/shelf'))).status).toBe(503);
  });

  it('relays a refusal as it is', async () => {
    fetchMock.mockResolvedValue(json(403, { detail: 'no' }));
    expect((await getShelf(req('/api/cockpit/shelf'))).status).toBe(403);
  });

  it('?shelf=0 asks the backend to leave the shelf out and returns no fixture cards', async () => {
    fetchMock.mockResolvedValue(json(200, { as_of_timestamp: '2026-10-16T00:00:00Z' }));
    const res = await getWorkstation(req('/api/cockpit/workstations/executive?shelf=0'), {
      params: Promise.resolve({ role: 'executive' }),
    });
    expect(String(fetchMock.mock.calls[0][0])).toContain('shelf=false');
    expect((await res.json()).stagedActionCards).toEqual([]);
  });
});
