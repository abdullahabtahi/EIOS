/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect } from 'vitest';
import { GET as getWorkstation } from '@/app/api/cockpit/workstations/[role]/route';
import { POST as postSimulate } from '@/app/api/cockpit/simulate/route';
import { POST as postAuthorize } from '@/app/api/cockpit/actions/authorize/route';
import { POST as postCopilotQuery } from '@/app/api/cockpit/copilot/query/route';
import { POST as postFeedback } from '@/app/api/cockpit/flywheel/feedback/route';
import { GET as getAuditVerify } from '@/app/api/cockpit/audit/verify/route';

describe('Next.js API Route Handlers Integration & Zero-Drift Bridge (User Story 6)', () => {
  it('GET /api/cockpit/workstations/[role] returns valid schema with deterministic fallback', async () => {
    const req = new Request('http://localhost:3000/api/cockpit/workstations/executive');
    const res = await getWorkstation(req as any, { params: Promise.resolve({ role: 'executive' }) });
    expect(res.status).toBe(200);

    const data = await res.json();
    expect(data.workstation).toBe('executive');
    expect(data.session).toBeDefined();
    expect(data.triageItems.length).toBeGreaterThan(0);
    expect(data.activeDossier).toBeDefined();
    expect(data.activeDossier.headline).toBeDefined();
    expect(data.canvasPayload).toBeDefined();
  });

  it('POST /api/cockpit/simulate verifies 100.0% (+/- 0.01%) waterfall attribution sum', async () => {
    const req = new Request('http://localhost:3000/api/cockpit/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ feeShockBps: 15 }),
    });

    const res = await postSimulate(req as any);
    expect(res.status).toBe(200);

    const data = await res.json();
    expect(data.propagationLatencyMs).toBeLessThan(200);
    const sum = data.attributionWaterfall.reduce(
      (acc: number, curr: any) => acc + curr.percentageShare,
      0
    );
    expect(Math.abs(sum - 100.0)).toBeLessThanOrEqual(0.01);
  });

  it('POST /api/cockpit/actions/authorize validates Cloud KMS signature and Four-Eyes record', async () => {
    const req = new Request('http://localhost:3000/api/cockpit/actions/authorize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        actionId: 'act_test_1',
        primaryOfficerId: 'OP_PRIMARY',
        secondaryOfficerId: 'OP_SECONDARY',
        rationale: 'Regulatory compliance verified',
      }),
    });

    const res = await postAuthorize(req as any);
    expect(res.status).toBe(200);

    const data = await res.json();
    expect(data.authorized).toBe(true);
    expect(data.signedReceipt).toBeDefined();
    expect(data.kmsKeyId).toContain('cryptoKeys');
  });

  it('POST /api/cockpit/copilot/query evaluates Metric Auditor Gate', async () => {
    const req = new Request('http://localhost:3000/api/cockpit/copilot/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: 'What is the LatAm spread impact?',
        role: 'executive',
      }),
    });

    const res = await postCopilotQuery(req as any);
    expect(res.status).toBe(200);

    const data = await res.json();
    expect(data.auditorResult).toBeDefined();
    expect(data.auditorResult.auditPassed).toBe(true);
    expect(data.citedMetrics.length).toBeGreaterThan(0);
  });

  it('POST /api/cockpit/flywheel/feedback records discrepancy to ledger', async () => {
    const req = new Request('http://localhost:3000/api/cockpit/flywheel/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        feedbackType: 'SAR_NARRATIVE_EDIT',
        entityId: 'ACC-88219',
        operatorId: 'OP_PRIMARY',
        operatorRationale: 'Adjusted statutory citations for FinCEN SAR filing',
        correctionText: 'Verified transaction flow loop of $1.42M',
      }),
    });

    const res = await postFeedback(req as any);
    expect(res.status).toBe(200);

    const data = await res.json();
    expect(data.logged).toBe(true);
    expect(data.feedbackId).toBeDefined();
  });

  it('GET /api/cockpit/audit/verify returns valid immutable WORM chain status', async () => {
    const res = await getAuditVerify();
    expect(res.status).toBe(200);

    const data = await res.json();
    expect(data.chainVerificationStatus).toBe('VALID');
    expect(data.recordsVerifiedCount).toBeGreaterThan(0);
  });
});
