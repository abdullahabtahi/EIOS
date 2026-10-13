import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act, within } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { OperationsBoardView } from '@/components/cockpit/workstations/operations-board';
import { GovernedActionShelf } from '@/components/cockpit/shell/governed-action-shelf';
import { HeaderNav } from '@/components/cockpit/shell/header-nav';
import { AppNavRail } from '@/components/cockpit/shell/app-nav-rail';
import { EXECUTIVE_FIXTURE, getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import type { ActionIntentCard, WorkstationApiResponse } from '@/components/cockpit/state/cockpit-types';

const breachedPayload = {
  sla_statuses: [
    { product_name: 'client_transactions', null_check_pass_rate: 0.9998, last_ingestion_timestamp: '2026-10-12T05:55:38Z', freshness_sla_seconds: 300, status: 'BREACHED' },
    { product_name: 'transactions_aml', null_check_pass_rate: 0.9999, last_ingestion_timestamp: '2026-10-12T05:55:38Z', freshness_sla_seconds: 180, status: 'BREACHED' },
  ],
  error_budgets: [{ slo_id: 'SLO-1', name: 'Streaming Ingestion Lag (<30s)', consumed_pct: 24.2, status: 'HEALTHY' }],
  red_line_gates: [{ gate_id: 'RL-1', name: 'Metric Calculation Determinism', status: 'PASS' }],
};

function mockFetchWith(resp: WorkstationApiResponse) {
  global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(resp) }) as unknown as typeof fetch;
}

afterEach(() => vi.restoreAllMocks());

describe('Operations Board reflects the real payload (no hard-coded HEALTHY)', () => {
  it('shows breaches from the live payload and never claims ALL HEALTHY', async () => {
    mockFetchWith({
      ...getMockWorkstationState('data_operations'),
      canvasPayload: { type: 'OPERATIONS_SLO', data: breachedPayload },
    });
    render(
      <CockpitProvider>
        <OperationsBoardView />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByText('2 OF 3 BREACHED')).toBeInTheDocument());
    expect(screen.queryByText(/ALL 6 DATA PRODUCTS HEALTHY/i)).not.toBeInTheDocument();
    expect(screen.getByText('client_transactions')).toBeInTheDocument();
    expect(screen.getByText('1/1 PASSING')).toBeInTheDocument();
    expect(screen.queryByText(/\[ILLUSTRATIVE\] baseline/i)).not.toBeInTheDocument();
  });

  it('flags the baseline as [ILLUSTRATIVE] when no usable payload arrives', async () => {
    mockFetchWith({ ...getMockWorkstationState('executive') });
    render(
      <CockpitProvider>
        <OperationsBoardView />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByText(/\[ILLUSTRATIVE\] baseline/i)).toBeInTheDocument());
  });
});

function Stager({ action }: { action: ActionIntentCard }) {
  const { stageAction } = useCockpit();
  return <button type="button" data-testid="stage" onClick={() => stageAction(action)} />;
}

describe('Governed Action Shelf never offers to execute an expired intent', () => {
  const expired: ActionIntentCard = {
    ...EXECUTIVE_FIXTURE.stagedActionCards[0],
    intentId: 'act_expired_test',
    lifecycleState: 'EXPIRED',
    severity: 'HIGH',
  };

  beforeEach(() => {
    mockFetchWith({ ...getMockWorkstationState('executive'), stagedActionCards: [] });
  });

  it('replaces Authorize/Execute with an Expired notice and drops the green verification claim', async () => {
    render(
      <CockpitProvider>
        <Stager action={expired} />
        <GovernedActionShelf />
      </CockpitProvider>,
    );
    await act(async () => {});
    await act(async () => {
      screen.getByTestId('stage').click();
    });
    const card = screen.getByTestId('action-card-act_expired_test');
    expect(within(card).queryByRole('button', { name: /Authorize|Execute/i })).not.toBeInTheDocument();
    expect(within(card).getByText(/Expired/i, { selector: '[data-testid="action-expired-notice"]' })).toBeInTheDocument();
    expect(within(card).queryByText(/DIGITALLY VERIFIED/i)).not.toBeInTheDocument();
    expect(within(card).getByRole('button', { name: /Discard/i })).toBeInTheDocument();
  });
});

describe('Telemetry is derived from state, not hard-coded', () => {
  it('header no longer prints a literal Lag: 18.4s or an unconditional Synced', async () => {
    mockFetchWith({ ...getMockWorkstationState('executive'), dataOrigin: 'live' });
    render(
      <CockpitProvider>
        <HeaderNav />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('header-pipeline-status')).toHaveTextContent(/Live/));
    expect(screen.queryByText('18.4s')).not.toBeInTheDocument();
    expect(screen.queryByText(/^Synced$/)).not.toBeInTheDocument();
  });

  it('header and rail both show Replay when the backend is unreachable', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('offline')) as unknown as typeof fetch;
    render(
      <CockpitProvider>
        <HeaderNav />
        <AppNavRail />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('header-pipeline-status')).toHaveTextContent(/Replay/));
    expect(screen.getByTestId('nav-pipeline-status')).toHaveTextContent(/Replay/);
  });

  it('header environment badge is not an unconditional PROD claim', () => {
    mockFetchWith({ ...getMockWorkstationState('executive') });
    render(
      <CockpitProvider>
        <HeaderNav />
      </CockpitProvider>,
    );
    expect(screen.queryByText(/^PROD/)).not.toBeInTheDocument();
  });
});
