import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { ComplianceExplorerView } from '@/components/cockpit/workstations/compliance-explorer';
import { normalizeLedger } from '@/lib/server/normalize-ledger';

const RAW = {
  entries: [
    { ledger_seq: 2, event_type: 'APPROVAL_RECORDED', entity_id: 'intent-1', actor_id: 'approver-1', prev_hash: 'aa', current_hash: 'bb', timestamp: '2026-10-14T08:01:00+00:00', is_worm_anchored: false },
    { ledger_seq: 1, event_type: 'PROPOSAL_CREATED', entity_id: 'intent-1', actor_id: 'analyst-1', prev_hash: '00', current_hash: 'aa', timestamp: '2026-10-14T08:00:00+00:00', is_worm_anchored: false },
  ],
  approvals: [
    { intent_id: 'intent-1', action_type: 'HoldWithdrawal', target_entity_id: 'CR84920', severity: 'HIGH', status: 'PENDING', requires_dual_approval: true, first_approver: { officer_id: 'approver-1', role: 'AML_INVESTIGATOR', approved_at: '2026-10-14T08:01:00+00:00' }, second_approver: null },
  ],
  checkpoints: [],
  verification: { total_entries_verified: 2, is_chain_unbroken: true, chain_head_hash: 'bb', worm_anchors_matched: 0 },
  is_simulated: false,
};

function respond(body: unknown, status = 200) {
  return Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });
}

afterEach(() => vi.restoreAllMocks());

describe('normalizeLedger', () => {
  it('maps the backend payload and reads missing fields as empty, never as a pass', () => {
    const ledger = normalizeLedger(RAW);
    expect(ledger.entries.map((e) => e.ledgerSeq)).toEqual([2, 1]);
    expect(ledger.approvals[0].second).toBeNull();
    expect(ledger.isSimulated).toBe(false);
    const empty = normalizeLedger({});
    expect(empty.verification.unbroken).toBe(false);
    expect(empty.isSimulated).toBe(true);
  });
});

describe('Compliance explorer reads the real decision ledger', () => {
  it('lists the entries and the sign-offs the backend returns', async () => {
    global.fetch = vi.fn().mockImplementation(() => respond(normalizeLedger(RAW))) as unknown as typeof fetch;
    render(<ComplianceExplorerView />);
    expect(await screen.findByText('SEQ #2')).toBeInTheDocument();
    expect(screen.getByText('SEQ #1')).toBeInTheDocument();
    expect(screen.getByText(/awaiting second approver/i)).toBeInTheDocument();
    expect(screen.getByText('No checkpoint taken yet')).toBeInTheDocument();
    expect(screen.queryByText(/SEC 17a-4|Hardware Retention/i)).toBeNull();
  });

  it('says the ledger is empty instead of showing sample rows', async () => {
    const empty = { ...RAW, entries: [], approvals: [], verification: { ...RAW.verification, total_entries_verified: 0 } };
    global.fetch = vi.fn().mockImplementation(() => respond(normalizeLedger(empty))) as unknown as typeof fetch;
    render(<ComplianceExplorerView />);
    expect(await screen.findByText(/no action has been staged yet/i)).toBeInTheDocument();
  });

  it('shows a failed load as a failure', async () => {
    global.fetch = vi.fn().mockImplementation(() => respond({ error: 'offline' }, 503)) as unknown as typeof fetch;
    render(<ComplianceExplorerView />);
    expect(await screen.findByRole('alert')).toHaveTextContent('HTTP 503');
  });

  it('runs the audit walk on the backend and shows its result', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string) =>
      url.includes('/audit/verify')
        ? respond({ status: 'TAMPERED', total_records: 2, worm_checkpoints_verified: 0, tampered_sequence_id: 2, verified_at: '2026-10-14T08:05:00+00:00' })
        : respond(normalizeLedger(RAW)),
    );
    global.fetch = fetchMock as unknown as typeof fetch;
    render(<ComplianceExplorerView />);
    fireEvent.click(await screen.findByRole('button', { name: /Verify Chain Continuity/i }));
    await waitFor(() => expect(screen.getByText('Break at entry 2')).toBeInTheDocument());
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes('/api/cockpit/audit/verify'))).toBe(true);
  });
});
