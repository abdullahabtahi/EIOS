import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { authorizeIntent, GovernedActionError, stageProposal } from '@/lib/actions/governed-actions';
import type { StageRequest } from '@/components/cockpit/state/cockpit-types';

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const request: StageRequest = {
  action_type: 'HoldWithdrawal',
  target_entity_id: 'CR84920',
  severity: 'HIGH',
  requires_four_eyes: true,
  metadata: { txn_id: 'W-84920-1', reason: 'Held for review' },
};

const backendCard = (overrides: Record<string, unknown> = {}) => ({
  intent_id: 'intent-1',
  action_type: 'HoldWithdrawal',
  target_entity_id: 'CR84920',
  severity: 'HIGH',
  lifecycle_state: 'STAGED',
  requires_four_eyes: true,
  kms_signature: { key_id: 'projects/p/keys/k', algorithm: 'ECDSA_P256_SHA256', signature_digest: 'MEUC', verified: true },
  ...overrides,
});

describe('stageProposal', () => {
  it('sends the backend-built request unchanged and returns the card the backend made', async () => {
    fetchMock.mockResolvedValue(json({ status: 'STAGED', card: backendCard(), total_staged: 1 }));
    const card = await stageProposal(request);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/cockpit/actions/stage');
    expect(JSON.parse(init.body)).toEqual(request);
    expect(card.intentId).toBe('intent-1');
    expect(card.lifecycleState).toBe('STAGED');
    expect(card.kmsSignatureBadge.verified).toBe(true);
  });

  it('never invents a card when the backend returns none', async () => {
    fetchMock.mockResolvedValue(json({ status: 'STAGED' }));
    await expect(stageProposal(request)).rejects.toBeInstanceOf(GovernedActionError);
  });

  it.each([
    [401, 'Sign in again'],
    [403, 'role is not permitted'],
    [422, 'missing required parameter'],
    [503, 'offline'],
  ])('reports a backend %i as the operator-readable reason, not a staged card', async (status, expected) => {
    fetchMock.mockResolvedValue(json({ detail: status === 422 ? 'missing required parameter txn_id' : 'x' }, status));
    const error = await stageProposal(request).catch((e) => e);
    expect(error).toBeInstanceOf(GovernedActionError);
    expect(error.status).toBe(status);
    expect(error.message.toLowerCase()).toContain(expected.toLowerCase());
  });

  it('reports an unreachable backend as no card', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    const error = await stageProposal(request).catch((e) => e);
    expect(error.status).toBeNull();
    expect(error.message).toContain('could not be reached');
  });
});

describe('authorizeIntent', () => {
  it('posts the fields the backend reads and takes the lifecycle state from its card', async () => {
    fetchMock.mockResolvedValue(
      json({ status: 'PENDING_SECOND_EYE', card: backendCard({ lifecycle_state: 'PENDING_SECOND_EYE' }), committed_timestamp: null }),
    );
    const result = await authorizeIntent('intent-1', 'officer-7');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/cockpit/actions/authorize');
    expect(JSON.parse(init.body)).toEqual({ intent_id: 'intent-1', authorizer_id: 'officer-7' });
    expect(result.status).toBe('PENDING_SECOND_EYE');
    expect(result.card.lifecycleState).toBe('PENDING_SECOND_EYE');
  });

  it('does not fabricate a commit when the backend refuses', async () => {
    fetchMock.mockResolvedValue(json({ detail: 'Four-Eyes violation: second approver must differ' }, 400));
    const error = await authorizeIntent('intent-1', 'officer-7').catch((e) => e);
    expect(error).toBeInstanceOf(GovernedActionError);
    expect(error.status).toBe(400);
    expect(error.message).toContain('Four-Eyes violation');
  });

  it('does not fabricate a commit when the backend is down', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    const error = await authorizeIntent('intent-1', 'officer-7').catch((e) => e);
    expect(error.status).toBeNull();
  });
});
