import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { OperationsBoardView } from '@/components/cockpit/workstations/operations-board';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';

describe('Operations Board (User Story 5)', () => {
  it('shows the cards and the red-line gates the backend sent, with an unmeasured gate marked as such', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          ...getMockWorkstationState('data_operations'),
          canvasPayload: {
            type: 'OPERATIONS_SLO',
            data: {
              sla_statuses: [{ product_name: 'partner_comms', status: 'HEALTHY', freshness_sla_seconds: 900, null_check_pass_rate: 1, last_ingestion_timestamp: '2026-10-14T07:55:00Z' }],
              error_budgets: [],
              red_line_gates: [
                { gate_id: 'RL-1', name: 'Zero LLM Metric Calculation', status: 'PASS' },
                { gate_id: 'RL-7', name: 'Deterministic Offline Replay Fallback', status: 'NOT_MEASURED' },
              ],
              dlq: [],
            },
          },
        }),
    }) as unknown as typeof fetch;
    render(
      <CockpitProvider>
        <OperationsBoardView />
      </CockpitProvider>,
    );
    expect(await screen.findByText('partner_comms')).toBeInTheDocument();
    expect(screen.getByText(/Continuous Governance Red-Line Gates/i)).toBeInTheDocument();
    expect(screen.getByText(/RL-1:/i)).toBeInTheDocument();
    expect(screen.getByText(/RL-7:/i)).toBeInTheDocument();
    expect(screen.getByText('NOT MEASURED')).toBeInTheDocument();
    expect(screen.queryByText(/Raw Ingestion Pipeline/i)).not.toBeInTheDocument();
  });
});
