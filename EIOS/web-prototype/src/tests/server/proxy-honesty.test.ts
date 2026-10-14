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
    assistant_status: 'ASSEMBLED',
    fallback_reason: null,
    provenance_citations: [{ metric_id: 'net_revenue_usd', formatted_value: 'Net revenue', steward: 'DuckDB', as_of: '2026-01-02T03:04:05+00:00' }],
    ...overrides,
  });

  describe('an ADK assistant answer', () => {
    const adk = (overrides: Record<string, unknown> = {}) =>
      upstream({
        failed_closed: false,
        blocked: false,
        block_reason: null,
        data_origin: 'fixture',
        steps: ['get_aml_dossier'],
        turn_latency_ms: 4200,
        provenance_citations: [
          {
            metric_id: 'aml.dossier:CR84920:discrepancy_multiplier',
            formatted_value: '16x',
            raw_value: 16,
            unit: 'multiplier',
            data_origin: 'fixture',
            source: 'cockpit.aml.get_entity_dossier',
            steward: 'cockpit.aml.get_entity_dossier',
            as_of: '2026-10-14T03:57:10+00:00',
          },
        ],
        proposals: [],
        ...overrides,
      });

    it('is carried as an assembled answer, with no audit claim of any kind', async () => {
      fetchMock.mockResolvedValue(json(adk()));
      const body = await (await post()).json();
      expect(body.assistantStatus).toBe('ASSEMBLED');
      expect(body.auditorResult).toBeUndefined(); // the Metric Auditor did not run, and is never claimed
      expect(body.suggestedAction).toBeUndefined();
      expect(body.isReplayFallback).toBeUndefined();
      expect(body.dataOrigin).toBe('fixture');
      expect(body.steps).toEqual(['get_aml_dossier']);
    });

    it('keeps each figure with its unit, value, source, as-of and data origin', async () => {
      fetchMock.mockResolvedValue(json(adk()));
      const [metric] = (await (await post()).json()).citedMetrics;
      expect(metric.formattedValue).toBe('16x');
      expect(metric.rawValue).toBe(16);
      expect(metric.unit).toBe('multiplier');
      expect(metric.dataOrigin).toBe('fixture');
      expect(metric.originEngine).toBe('cockpit.aml.get_entity_dossier');
      expect(metric.asOfTimestamp).toBe('2026-10-14T03:57:10+00:00');
    });

    it('labels a figure live only when the backend says so', async () => {
      fetchMock.mockResolvedValue(json(adk({ provenance_citations: [{ metric_id: 'x', formatted_value: '1', data_origin: 'weird' }] })));
      expect((await (await post()).json()).citedMetrics[0].dataOrigin).toBeUndefined();
    });

    it('refuses an answer whose status it cannot read instead of guessing a pass', async () => {
      fetchMock.mockResolvedValue(json(adk({ assistant_status: 'SOMETHING_NEW' })));
      expect((await post()).status).toBe(502);
      fetchMock.mockResolvedValue(json(adk({ assistant_status: undefined })));
      expect((await post()).status).toBe(502);
    });

    it('says blocked, with the reason, and fails closed on an unknown status', async () => {
      fetchMock.mockResolvedValue(json(adk({ assistant_status: 'BLOCKED', blocked: true, block_reason: 'input', provenance_citations: [] })));
      const blocked = await (await post()).json();
      expect(blocked.assistantStatus).toBe('BLOCKED');
      expect(blocked.blockReason).toBe('input');

      fetchMock.mockResolvedValue(json(adk({ assistant_status: 'BLOCKED', blocked: true, block_reason: 'output', provenance_citations: [] })));
      expect((await (await post()).json()).blockReason).toBe('output');
    });

    it('carries a fail-closed answer with no figures', async () => {
      fetchMock.mockResolvedValue(json(adk({ assistant_status: 'FAILED_CLOSED', failed_closed: true, provenance_citations: [] })));
      const body = await (await post()).json();
      expect(body.assistantStatus).toBe('FAILED_CLOSED');
      expect(body.citedMetrics).toEqual([]);
    });

    it('carries a proposal with the backend-built stage request, unsigned and not staged', async () => {
      const stageRequest = {
        action_type: 'HoldWithdrawal',
        target_entity_id: 'CR84920',
        severity: 'HIGH',
        requires_four_eyes: true,
        metadata: { txn_id: 'W-84920-1', reason: 'Held for review' },
      };
      fetchMock.mockResolvedValue(
        json(
          adk({
            proposals: [
              {
                proposal_ref: 'prop-1',
                kind: 'hold_withdrawal',
                label: 'Hold a pending withdrawal for review',
                offer: 'Hold withdrawal W-84920-1',
                estimated_cost_usd: 0,
                expected_effect_low: 7800,
                expected_effect_high: 7800,
                expected_effect_basis: 'The full pending withdrawal stays',
                approval_requirement: 'Dual approval',
                signed: false,
                staged: false,
                data_origin: 'fixture',
                source: 'port.aml_fixtures',
                as_of: '2026-10-14T03:57:10+00:00',
                stage_request: stageRequest,
              },
            ],
          }),
        ),
      );
      const [proposal] = (await (await post()).json()).proposals;
      expect(proposal.proposalRef).toBe('prop-1');
      expect(proposal.stageRequest).toEqual(stageRequest);
      expect(proposal.signed).toBe(false);
      expect(proposal.staged).toBe(false);
    });

    it('drops a proposal that carries no stage request: it cannot be acted on', async () => {
      fetchMock.mockResolvedValue(json(adk({ proposals: [{ proposal_ref: 'prop-2', kind: 'hold_withdrawal' }] })));
      expect((await (await post()).json()).proposals).toEqual([]);
    });

    it('relays the offline 503 body so the UI can say the assistant is unavailable', async () => {
      fetchMock.mockResolvedValue(json({ detail: 'offline', fallback_reason: 'RuntimeError' }, 503));
      const res = await post();
      expect(res.status).toBe(503);
      expect((await res.json()).detail).toBe('offline');
    });
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

  it('labels backend data as fixture unless the backend itself says it is live', async () => {
    fetchMock.mockResolvedValue(json({ fallback_state: { is_active: false, badge_label: '[ILLUSTRATIVE]' } }));
    expect((await (await get()).json()).dataOrigin).toBe('fixture');

    fetchMock.mockResolvedValue(json({}));
    expect((await (await get()).json()).dataOrigin).toBe('fixture');

    fetchMock.mockResolvedValue(json({ fallback_state: { is_active: false, badge_label: '[LIVE]' } }));
    expect((await (await get()).json()).dataOrigin).toBe('live');
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
