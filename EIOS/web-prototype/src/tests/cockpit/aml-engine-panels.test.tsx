import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { EvidenceStripPanel } from '@/components/cockpit/common/evidence-strip';
import { SarComposer } from '@/components/cockpit/common/sar-composer';
import { AmlWorkstationView } from '@/components/cockpit/workstations/aml-workstation';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import { normalizeCaseExtras } from '@/lib/server/normalize';
import type { EvidenceStrip, SarDraftDocument, WorkstationApiResponse } from '@/components/cockpit/state/cockpit-types';

const strip: EvidenceStrip = {
  title: 'One-Screen Evidence Dossier: CR91539 (CO)',
  severity: 'CRITICAL',
  score: 0.95,
  tiles: [
    { label: '30-day deposits', value: '$1,500', caption: '1.9x declared income', tone: 'neutral' },
    { label: 'Network', value: '7 accounts', caption: 'share a device fingerprint', tone: 'alert' },
  ],
  metrics: [],
};

const sar: SarDraftDocument = {
  caseId: 'case_aml_CR91539',
  subjectName: 'Account CR91539',
  subjectAccountId: 'CR91539',
  suspiciousActivityType: 'Mule Syndicate',
  summaryNarrative: 'Investigation of subject account #CR91539.',
  transactionHistorySummary: '2 deposits and 1 withdrawal in 30 days.',
  totalTurnover: 1500,
  statutoryCitations: [],
  statutoryNote: 'Statutory citations attach once regulation retrieval is connected.',
  generatedTimestamp: '2026-10-14T08:00:00Z',
  status: 'DRAFT',
};

const stageRequest = {
  action_type: 'FileSARDraft',
  target_entity_id: 'CR91539',
  severity: 'MEDIUM',
  requires_four_eyes: true,
  metadata: { case_id: 'case_aml_CR91539', template_id: 'FinCEN_SAR_v1' },
};

const engineResponse = (): WorkstationApiResponse => ({
  ...getMockWorkstationState('aml_investigator'),
  dataOrigin: 'engine',
  evidenceStrip: strip,
  sarDraft: sar,
  caseActions: { hold: null, fileSar: stageRequest },
});

function Open() {
  const { setRole } = useCockpit();
  return <button type="button" data-testid="go" onClick={() => setRole('aml_investigator')} />;
}

describe('AML engine panels read the selected case, never a sample', () => {
  it('renders the strip title, tiles and tone from the backend', () => {
    render(<EvidenceStripPanel strip={strip} />);
    expect(screen.getByText('One-Screen Evidence Dossier: CR91539 (CO)')).toBeInTheDocument();
    expect(screen.getAllByTestId('evidence-tile')).toHaveLength(2);
    expect(screen.getByText('SEVERITY: CRITICAL (SCORE: 0.95)')).toBeInTheDocument();
    expect(screen.getByText('7 accounts')).toHaveClass('text-red-700');
    expect(screen.queryByText(/88219|1,420,000|LatAm/)).not.toBeInTheDocument();
  });

  it('says there is no alert instead of inventing a severity', () => {
    render(<EvidenceStripPanel strip={{ ...strip, score: null, severity: 'NONE' }} />);
    expect(screen.getByText('NO ALERT')).toBeInTheDocument();
  });

  it('normalises the extras and keeps absent parts absent', () => {
    expect(normalizeCaseExtras({})).toEqual({ evidenceStrip: undefined, sarDraft: undefined, caseActions: undefined });
    const got = normalizeCaseExtras({
      evidence_strip: { title: 't', severity: 'HIGH', score: 0.7, tiles: [], metrics: [{ metric_id: 'm', citation: '[COMPUTED]' }] },
      case_actions: { hold: null, file_sar: stageRequest },
    });
    expect(got.evidenceStrip?.metrics[0].citation).toBe('[COMPUTED]');
    expect(got.caseActions).toEqual({ hold: null, fileSar: stageRequest });
  });
});

describe('Engine-backed AML workstation', () => {
  let calls: Array<{ url: string; body?: string }>;

  beforeEach(() => {
    calls = [];
    global.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      calls.push({ url, body: init?.body as string | undefined });
      if (url.includes('/actions/stage')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              status: 'STAGED',
              card: { intent_id: 'intent-1', action_type: 'FileSARDraft', target_entity_id: 'case_aml_CR91539', lifecycle_state: 'STAGED', kms_signature: { key_id: 'k', algorithm: 'ECDSA_P256_SHA256', signature_digest: 'd', verified: true } },
            }),
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(engineResponse()) });
    }) as unknown as typeof fetch;
  });
  afterEach(() => vi.restoreAllMocks());

  const mount = async (ui: React.ReactNode) => {
    render(
      <CockpitProvider>
        <Open />
        {ui}
      </CockpitProvider>,
    );
    await act(async () => {
      screen.getByTestId('go').click();
    });
    await waitFor(() => expect(screen.queryByTestId('sar-loading')).not.toBeInTheDocument());
  };

  it('shows the engine strip and no fixture account in the workstation', async () => {
    await mount(<AmlWorkstationView />);
    await waitFor(() => expect(screen.getByText('One-Screen Evidence Dossier: CR91539 (CO)')).toBeInTheDocument());
    expect(screen.queryByText(/ACC-88219/)).not.toBeInTheDocument();
  });

  it('composes the SAR from the case and says why it has no statutory citations', async () => {
    await mount(<SarComposer />);
    expect(screen.getByDisplayValue('Investigation of subject account #CR91539.')).toBeInTheDocument();
    expect(screen.getByTestId('sar-no-citations')).toHaveTextContent('regulation retrieval is connected');
    expect(screen.queryByText(/31 U.S.C./)).not.toBeInTheDocument();
  });

  it('stages the filing through the backend, with the backend request, and shows the shelf card the hub made', async () => {
    await mount(<SarComposer />);
    fireEvent.click(screen.getByRole('button', { name: /Stage Official SAR Filing/ }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Staged FileSARDraft'));
    const stage = calls.find((c) => c.url.includes('/actions/stage'));
    expect(JSON.parse(stage?.body ?? '{}')).toEqual(stageRequest);
  });

  it('disables filing when the case has no filing action', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ ...engineResponse(), caseActions: { hold: null, fileSar: null } }),
    }) as unknown as typeof fetch;
    await mount(<SarComposer />);
    expect(screen.getByRole('button', { name: /Stage Official SAR Filing/ })).toBeDisabled();
  });
});
