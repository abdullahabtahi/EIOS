import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { normalizeActionCard } from '@/lib/server/normalize';
import { POST as copilotQuery } from '@/app/api/cockpit/copilot/query/route';
import { GET as workstation } from '@/app/api/cockpit/workstations/[role]/route';

const fetchMock = vi.fn();
beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const backendCard = (overrides: Record<string, unknown> = {}) => ({
  intent_id: 'act_1',
  action_type: 'HoldWithdrawal',
  target_entity_id: 'ACC-1',
  severity: 'HIGH',
  lifecycle_state: 'STAGED',
  requires_four_eyes: true,
  initiator_officer_id: 'OFFICER_A',
  kms_signature: { key_id: 'projects/p/keys/k', algorithm: 'ECDSA_P256_SHA256', signature_digest: 'MEUCIQ', verified: true },
  ...overrides,
});

describe('normalizeActionCard fails closed', () => {
  it('reports the backend-verified signature as verified, with its real key and digest', () => {
    const card = normalizeActionCard(backendCard());
    expect(card.kmsSignatureBadge).toEqual({
      keyId: 'projects/p/keys/k',
      algorithm: 'ECDSA_P256_SHA256',
      signatureDigest: 'MEUCIQ',
      verified: true,
    });
  });

  it('never upgrades an unverified or missing signature to verified', () => {
    expect(normalizeActionCard(backendCard({ kms_signature: { verified: false } })).kmsSignatureBadge.verified).toBe(false);
    expect(normalizeActionCard(backendCard({ kms_signature: undefined })).kmsSignatureBadge.verified).toBe(false);
    expect(normalizeActionCard(backendCard({ kms_signature: { verified: 'yes' } })).kmsSignatureBadge.verified).toBe(false);
  });

  it('does not invent a key id, digest, or identity-provider validation', () => {
    const card = normalizeActionCard(backendCard({ kms_signature: undefined }));
    expect(card.kmsSignatureBadge.keyId).toBe('');
    expect(card.kmsSignatureBadge.signatureDigest).toBe('');
    expect(card.fourEyesRecord.idpClaimValidation).toBe(false);
  });
});

describe('copilot proxy', () => {
  const post = (body: unknown = { query: 'q', role: 'executive' }) =>
    copilotQuery(new NextRequest('http://localhost/api/cockpit/copilot/query', { method: 'POST', body: JSON.stringify(body) }));

  const upstream = (overrides: Record<string, unknown> = {}) => ({
    query: 'q',
    response: 'Net revenue is $3,820,000.',
    auditor_status: 'PASS',
    is_replay_fallback: false,
    fallback_reason: null,
    provenance_citations: [{ metric_id: 'net_revenue_usd', formatted_value: 'Net revenue', steward: 'DuckDB', as_of: '2026-01-02T03:04:05+00:00' }],
    audit_record: { passed: true, unanchored_tokens: [], anchored_numbers: [3820000], relative_tolerance: 0.01 },
    tool_trace_count: 3,
    suggested_action: null,
    ...overrides,
  });

  it('reports the real audit, with no invented numbers or trace counts', async () => {
    fetchMock.mockResolvedValue(json(upstream()));
    const body = await (await post()).json();
    expect(body.auditorResult.auditPassed).toBe(true);
    expect(body.auditorResult.anchoredNumbers).toEqual([3820000]);
    expect(body.auditorResult.toolTracesCount).toBe(3);
    expect(JSON.stringify(body)).not.toContain('3,820,000"'); // the old hard-coded fixture string
    expect(body.citedMetrics[0].asOfTimestamp).toBe('2026-01-02T03:04:05+00:00');
  });

  it('carries is_replay_fallback and its reason to the browser', async () => {
    fetchMock.mockResolvedValue(json(upstream({ is_replay_fallback: true, fallback_reason: 'live Gemini call failed' })));
    const body = await (await post()).json();
    expect(body.isReplayFallback).toBe(true);
    expect(body.fallbackReason).toBe('live Gemini call failed');
  });

  it('never treats a missing or UNAUDITED audit as a pass', async () => {
    fetchMock.mockResolvedValue(json(upstream({ auditor_status: 'UNAUDITED', audit_record: { passed: false, unanchored_tokens: [], anchored_numbers: [] } })));
    const body = await (await post()).json();
    expect(body.auditorResult.auditPassed).toBe(false);
  });

  it('does not sign a suggested action the backend left unsigned', async () => {
    fetchMock.mockResolvedValue(json(upstream({ suggested_action: { intent_id: 'rec_1', action_type: 'HoldWithdrawal', target_entity_id: 'ACC-1' } })));
    const body = await (await post()).json();
    expect(body.suggestedAction.kmsSignatureBadge.verified).toBe(false);
    expect(body.suggestedAction.kmsSignatureBadge.signatureDigest).toBe('');
  });

  it.each([401, 403, 422, 500])('relays a backend %i instead of fabricating an answer', async (status) => {
    fetchMock.mockResolvedValue(json({ detail: 'nope' }, status));
    const res = await post();
    expect(res.status).toBe(status);
    expect((await res.json()).detail).toBe('nope');
  });

  it('answers 503 offline when the backend is unreachable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    const res = await post();
    expect(res.status).toBe(503);
    expect((await res.json()).offline).toBe(true);
  });
});

describe('workstation proxy', () => {
  const get = () =>
    workstation(new NextRequest('http://localhost/api/cockpit/workstations/executive'), {
      params: Promise.resolve({ role: 'executive' }),
    });

  it('reads the backend kms_signature and does not default verified to true', async () => {
    fetchMock.mockResolvedValue(
      json({ governed_action_shelf: { actions: [backendCard({ intent_id: 'a' }), backendCard({ intent_id: 'b', kms_signature: undefined })] } }),
    );
    const body = await (await get()).json();
    const [signed, unsigned] = body.stagedActionCards;
    expect(signed.kmsSignatureBadge.verified).toBe(true);
    expect(signed.kmsSignatureBadge.keyId).toBe('projects/p/keys/k');
    expect(unsigned.kmsSignatureBadge.verified).toBe(false);
  });

  it('relays 401/403 and labels any outage fallback as a replay', async () => {
    fetchMock.mockResolvedValue(json({ detail: 'expired' }, 401));
    expect((await get()).status).toBe(401);

    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    const body = await (await get()).json();
    expect(body.isLiveConnected).toBe(false);
    expect(body.isCachedFallback).toBe(true);
  });
});
