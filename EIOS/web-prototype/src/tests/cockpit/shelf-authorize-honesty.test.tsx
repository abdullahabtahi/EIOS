import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { GovernedActionShelf } from '@/components/cockpit/shell/governed-action-shelf';
import { EXECUTIVE_FIXTURE, getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import type { ActionIntentCard } from '@/components/cockpit/state/cockpit-types';

const staged: ActionIntentCard = {
  ...EXECUTIVE_FIXTURE.stagedActionCards[0],
  intentId: 'intent-hold-1',
  lifecycleState: 'STAGED',
  severity: 'HIGH',
  requiresFourEyes: true,
  kmsSignatureBadge: { keyId: 'projects/p/keys/k', algorithm: 'ECDSA_P256_SHA256', signatureDigest: 'MEUC', verified: false },
};

function Stager() {
  const { stageAction } = useCockpit();
  return <button type="button" data-testid="stage" onClick={() => stageAction(staged)} />;
}

const backendCard = (lifecycle: string) => ({
  intent_id: 'intent-hold-1',
  action_type: 'HoldWithdrawal',
  target_entity_id: 'CR84920',
  severity: 'HIGH',
  lifecycle_state: lifecycle,
  requires_four_eyes: true,
  kms_signature: { key_id: 'projects/p/keys/k', algorithm: 'ECDSA_P256_SHA256', signature_digest: 'MEUC', verified: true },
});

function mockBackend(authorize: () => Promise<unknown>) {
  const fn = vi.fn().mockImplementation((url: string) =>
    String(url).includes('/api/cockpit/actions/authorize')
      ? authorize()
      : Promise.resolve({ ok: true, json: () => Promise.resolve({ ...getMockWorkstationState('executive'), stagedActionCards: [] }) }),
  );
  global.fetch = fn as unknown as typeof fetch;
  return fn;
}

async function openFourEyes() {
  render(
    <CockpitProvider>
      <Stager />
      <GovernedActionShelf />
    </CockpitProvider>,
  );
  await act(async () => {});
  await act(async () => {
    screen.getByTestId('stage').click();
  });
  const card = screen.getByTestId('action-card-intent-hold-1');
  fireEvent.click(within(card).getByRole('button', { name: /Authorize \(Four-Eyes\)/i }));
  return card;
}

beforeEach(() => vi.restoreAllMocks());
afterEach(() => vi.restoreAllMocks());

describe('authorizing from the shelf goes to the backend and shows only what it returned', () => {
  it('posts the fields the backend reads and shows the lifecycle state the backend gave', async () => {
    const fetchMock = mockBackend(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ status: 'PENDING_SECOND_EYE', card: backendCard('PENDING_SECOND_EYE') }) }),
    );
    await openFourEyes();
    fireEvent.click(await screen.findByRole('button', { name: /^Authorize$/ }));
    await waitFor(() => expect(screen.getByTestId('action-card-intent-hold-1')).toHaveTextContent(/PENDING_SECOND_EYE|second/i));
    const call = fetchMock.mock.calls.find(([u]) => String(u).includes('/actions/authorize'))!;
    const body = JSON.parse(call[1].body);
    expect(body.intent_id).toBe('intent-hold-1');
    expect(body.intentId).toBeUndefined();
    expect(screen.getByTestId('action-card-intent-hold-1')).not.toHaveTextContent(/COMMITTED TO WORM LEDGER/i);
  });

  it('never marks the action committed when the backend refuses', async () => {
    mockBackend(() => Promise.resolve({ ok: false, status: 400, json: () => Promise.resolve({ detail: 'Four-Eyes violation: second approver must differ' }) }));
    await openFourEyes();
    fireEvent.click(await screen.findByRole('button', { name: /^Authorize$/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/Four-Eyes violation/);
    expect(screen.getByTestId('action-card-intent-hold-1')).not.toHaveTextContent(/COMMITTED TO WORM LEDGER/i);
    expect(screen.queryByText(/RECEIPT_KMS/)).not.toBeInTheDocument();
  });

  it('never marks the action committed when the backend is unreachable', async () => {
    mockBackend(() => Promise.reject(new TypeError('fetch failed')));
    await openFourEyes();
    fireEvent.click(await screen.findByRole('button', { name: /^Authorize$/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be reached/i);
    expect(screen.getByTestId('action-card-intent-hold-1')).not.toHaveTextContent(/COMMITTED TO WORM LEDGER/i);
  });
});
