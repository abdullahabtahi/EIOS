/* eslint-disable @typescript-eslint/no-explicit-any */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET as getWorkstation } from '@/app/api/cockpit/workstations/[role]/route';
import { POST as postSimulate } from '@/app/api/cockpit/simulate/route';
import { POST as postStage } from '@/app/api/cockpit/actions/stage/route';
import { POST as postAuthorize } from '@/app/api/cockpit/actions/authorize/route';
import { POST as postCopilotQuery } from '@/app/api/cockpit/copilot/query/route';
import { POST as postFeedback } from '@/app/api/cockpit/flywheel/feedback/route';
import { GET as getAuditVerify } from '@/app/api/cockpit/audit/verify/route';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const post = (path: string, body: unknown = {}, headers: Record<string, string> = {}) =>
  new Request(`http://localhost:3000${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  });

const writeRoutes: Array<[string, string, (req: any) => Promise<Response>]> = [
  ['stage', '/api/cockpit/actions/stage', postStage],
  ['authorize', '/api/cockpit/actions/authorize', postAuthorize],
  ['simulate', '/api/cockpit/simulate', postSimulate],
  ['copilot query', '/api/cockpit/copilot/query', postCopilotQuery],
  ['flywheel feedback', '/api/cockpit/flywheel/feedback', postFeedback],
];

describe('Cockpit API proxy routes never fabricate a backend answer', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe.each(writeRoutes)('%s', (_name, path, handler) => {
    it('reports an unreachable backend as 503 offline, not as a success', async () => {
      fetchMock.mockRejectedValue(new Error('connect ECONNREFUSED'));
      const res = await handler(post(path));
      expect(res.status).toBe(503);
      expect((await res.json()).offline).toBe(true);
    });

    it('passes the backend rejection through with its own status and detail', async () => {
      fetchMock.mockResolvedValue(json(400, { detail: 'Four-Eyes Violation: cannot approve own intent' }));
      const res = await handler(post(path));
      expect(res.status).toBe(400);
      expect((await res.json()).detail).toContain('Four-Eyes');
    });

    it('relays 401 so the operator is sent to sign in', async () => {
      fetchMock.mockResolvedValue(json(401, { detail: 'Authentication required' }));
      expect((await handler(post(path))).status).toBe(401);
    });

    it('forwards the operator token to the backend', async () => {
      fetchMock.mockResolvedValue(json(200, { ok: true }));
      await handler(post(path, {}, { Authorization: 'Bearer abc.def.ghi' }));
      const sent = fetchMock.mock.calls[0][1].headers as Headers;
      expect(sent.get('Authorization')).toBe('Bearer abc.def.ghi');
    });
  });

  it('stage and authorize relay the backend body untouched on success', async () => {
    fetchMock.mockResolvedValue(json(200, { status: 'COMMITTED', card: { intent_id: 'i-1' } }));
    const res = await postAuthorize(post('/api/cockpit/actions/authorize', { intent_id: 'i-1' }) as any);
    expect(await res.json()).toEqual({ status: 'COMMITTED', card: { intent_id: 'i-1' } });
  });

  it('audit verify never reports VALID without asking the backend', async () => {
    fetchMock.mockRejectedValue(new Error('down'));
    const res = await getAuditVerify(new Request('http://localhost:3000/api/cockpit/audit/verify') as any);
    expect(res.status).toBe(503);
    expect(await res.json()).not.toHaveProperty('chainVerificationStatus');
  });

  describe('workstations', () => {
    const call = (role = 'executive') =>
      getWorkstation(new Request(`http://localhost:3000/api/cockpit/workstations/${role}`) as any, {
        params: Promise.resolve({ role }),
      });

    it('serves a labelled replay snapshot when the backend is unreachable', async () => {
      fetchMock.mockRejectedValue(new Error('down'));
      const res = await call();
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.isCachedFallback).toBe(true);
      expect(data.isLiveConnected).toBe(false);
      expect(data.fallbackReason).toBeTruthy();
      expect(data.triageItems.length).toBeGreaterThan(0);
    });

    it('does not mask an authentication failure with a snapshot', async () => {
      fetchMock.mockResolvedValue(json(401, { detail: 'Authentication required' }));
      expect((await call()).status).toBe(401);
    });

    it('does not mask a forbidden role with a snapshot', async () => {
      fetchMock.mockResolvedValue(json(403, { detail: 'Operator has no recognised role' }));
      expect((await call()).status).toBe(403);
    });
  });
});
