import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { CopilotCommandBar } from '@/components/cockpit/shell/copilot-command-bar';

const workstationBody = {
  workstation: 'executive',
  isLiveConnected: true,
  isCachedFallback: false,
  asOfTimestamp: '2026-10-10T10:00:00Z',
  session: { sessionId: 'test', systemLatencyMs: 12 },
  triageItems: [],
  activeDossier: null,
  stagedActionCards: [],
};

const figure = {
  metricId: 'aml.dossier:CR84920:discrepancy_multiplier',
  name: 'discrepancy multiplier',
  rawValue: 16,
  formattedValue: '16x',
  unit: 'multiplier',
  semanticDefinitionVersion: '',
  asOfTimestamp: '2026-10-14T03:57:10+00:00',
  originEngine: 'cockpit.aml.get_entity_dossier',
  stewardRole: 'cockpit.aml.get_entity_dossier',
  citation: '[ILLUSTRATIVE]',
  isCached: false,
  dataOrigin: 'fixture',
};

const assembled = (overrides: Record<string, unknown> = {}) => ({
  queryId: 'q1',
  naturalLanguageQuery: 'q',
  responseMarkdown: 'The discrepancy multiplier is 16x.',
  citedMetrics: [figure],
  auditorResult: { auditPassed: false, extractedNumbers: ['16x'], anchoredNumbers: ['16x'], untraceableNumbers: [], toolTracesCount: 1 },
  assistantStatus: 'ASSEMBLED',
  dataOrigin: 'fixture',
  steps: ['get_aml_dossier'],
  proposals: [],
  timestamp: '2026-10-14T03:57:10Z',
  ...overrides,
});

const stageRequest = {
  action_type: 'HoldWithdrawal',
  target_entity_id: 'CR84920',
  severity: 'HIGH',
  requires_four_eyes: true,
  metadata: { txn_id: 'W-84920-1', reason: 'Held for review' },
};

const proposal = {
  proposalRef: 'prop-1',
  kind: 'hold_withdrawal',
  label: 'Hold a pending withdrawal for review',
  offer: 'Hold withdrawal W-84920-1 on account CR84920',
  estimatedCostUsd: 0,
  expectedEffectLow: 7800,
  expectedEffectHigh: 7800,
  expectedEffectBasis: 'The full pending withdrawal stays in the account until review',
  approvalRequirement: 'Dual approval: a second approver is required',
  signed: false,
  staged: false,
  dataOrigin: 'fixture',
  source: 'port.aml_fixtures',
  asOf: '2026-10-14T03:57:10+00:00',
  stageRequest,
};

type Reply = () => Promise<unknown>;
function mockBackend(copilot: Reply, stage?: Reply) {
  const fn = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/api/cockpit/copilot/query')) return copilot();
    if (url.includes('/api/cockpit/actions/stage') && stage) return stage();
    return Promise.resolve({ ok: true, json: () => Promise.resolve(workstationBody) });
  });
  global.fetch = fn as unknown as typeof fetch;
  return fn;
}
const reply = (body: unknown, status = 200) => () => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });

async function ask(text = 'What is the discrepancy?') {
  render(
    <CockpitProvider>
      <CopilotCommandBar forceOpen={true} />
    </CockpitProvider>,
  );
  const input = screen.getAllByPlaceholderText(/Ask Copilot or type institutional command/i)[0];
  fireEvent.change(input, { target: { value: text } });
  fireEvent.submit(screen.getAllByRole('button', { name: /Submit Query/i })[0].closest('form')!);
}

afterEach(() => vi.restoreAllMocks());

describe('an ADK assistant answer in the command bar', () => {
  it('shows a clean answer with its figures and no status banner, DEMO chip or audit claim', async () => {
    mockBackend(reply(assembled()));
    await ask();
    await screen.findByText(figure.formattedValue);
    expect(screen.queryByText(/FIGURES FILLED FROM GOVERNED DATA/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/BLOCKED/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/AUDIT PASSED/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/did not run/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^demo$/i)).not.toBeInTheDocument();
    expect(screen.queryByText('[ILLUSTRATIVE]')).not.toBeInTheDocument();
    expect(screen.queryByTestId(/^figure-source-/)).not.toBeInTheDocument();
  });

  it('does not call data live unless the backend said so', async () => {
    mockBackend(reply(assembled({ dataOrigin: undefined, citedMetrics: [{ ...figure, dataOrigin: undefined }] })));
    await ask();
    await screen.findByText(figure.formattedValue);
    expect(screen.queryByText(/live data/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/real-time synchronized/i)).not.toBeInTheDocument();
  });

  it('says blocked, with the reason', async () => {
    mockBackend(reply(assembled({ assistantStatus: 'BLOCKED', blocked: true, blockReason: 'input', citedMetrics: [], responseMarkdown: 'Blocked.' })));
    await ask();
    expect(await screen.findByText(/BLOCKED BY POLICY/i)).toBeInTheDocument();
    expect(screen.getByText(/input screening/i)).toBeInTheDocument();
  });

  it('says it could not verify an answer and shows no figure', async () => {
    mockBackend(reply(assembled({ assistantStatus: 'FAILED_CLOSED', citedMetrics: [], responseMarkdown: 'I could not put together an answer.' })));
    await ask();
    expect(await screen.findByText(/COULD NOT VERIFY/i)).toBeInTheDocument();
  });

  it('shows a working indicator with elapsed time while the answer is pending', async () => {
    vi.useFakeTimers();
    try {
      mockBackend(() => new Promise(() => {}));
      await ask();
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(screen.getByRole('status')).toHaveTextContent(/working/i);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(12_000);
      });
      expect(screen.getByRole('status')).toHaveTextContent(/12 ?s/);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('a proposal from the assistant', () => {
  const withProposal = () => assembled({ responseMarkdown: 'I propose a hold; a second operator must approve it.', proposals: [proposal] });

  it('is offered for staging and says nothing is signed or sent yet', async () => {
    mockBackend(reply(withProposal()));
    await ask('Hold the withdrawal');
    expect(await screen.findByText(/Hold withdrawal W-84920-1/)).toBeInTheDocument();
    expect(screen.getByText(/nothing is signed or sent/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /stage proposal/i })).toBeEnabled();
  });

  it('is staged through the real stage endpoint with the backend-built request, and shows the backend card', async () => {
    const fetchMock = mockBackend(
      reply(withProposal()),
      reply({
        status: 'STAGED',
        card: { intent_id: 'intent-9', action_type: 'HoldWithdrawal', target_entity_id: 'CR84920', severity: 'HIGH', lifecycle_state: 'STAGED', requires_four_eyes: true, kms_signature: { verified: true, key_id: 'k' } },
        total_staged: 1,
      }),
    );
    await ask('Hold the withdrawal');
    fireEvent.click(await screen.findByRole('button', { name: /stage proposal/i }));
    await waitFor(() => expect(screen.getByText(/intent-9/)).toBeInTheDocument());
    const call = fetchMock.mock.calls.find(([url]) => String(url).includes('/api/cockpit/actions/stage'))!;
    expect(JSON.parse(call[1].body)).toEqual(stageRequest);
    expect(screen.getByText(/needs a second approver/i)).toBeInTheDocument();
    expect(screen.queryByText(/COMMITTED/i)).not.toBeInTheDocument();
  });

  it('shows the backend refusal and stages nothing when the role may not stage', async () => {
    mockBackend(reply(withProposal()), reply({ detail: 'forbidden' }, 403));
    await ask('Hold the withdrawal');
    fireEvent.click(await screen.findByRole('button', { name: /stage proposal/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/not permitted/i);
    expect(screen.getByRole('button', { name: /stage proposal/i })).toBeEnabled();
  });
});
