import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { ComplianceExplorerView } from '@/components/cockpit/workstations/compliance-explorer';
import { OperationsBoardView } from '@/components/cockpit/workstations/operations-board';

describe('Compliance Explorer & Operations Board (User Story 5)', () => {
  it('renders Compliance Explorer with monotonic ledger and verifies chain continuity', () => {
    render(
      <CockpitProvider>
        <ComplianceExplorerView />
      </CockpitProvider>
    );

    expect(screen.getByText(/WORM Cryptographic Ledger Chain/i)).toBeInTheDocument();
    expect(screen.getByText(/SEQ #10482/i)).toBeInTheDocument();
    expect(screen.getByText(/HOLD_WITHDRAWAL/i)).toBeInTheDocument();

    const verifyBtn = screen.getByRole('button', { name: /Verify Chain Continuity/i });
    expect(verifyBtn).toBeInTheDocument();
    fireEvent.click(verifyBtn);
  });

  it('renders Operations Board with 6 Data Product SLA monitors and 7 Red-Line test gates', () => {
    render(
      <CockpitProvider>
        <OperationsBoardView />
      </CockpitProvider>
    );

    expect(screen.getByText(/Data Product SLA Freshness & Error Budget Burndowns/i)).toBeInTheDocument();
    expect(screen.getByText(/Raw Ingestion Pipeline/i)).toBeInTheDocument();
    expect(screen.getByText(/DuckDB Semantic Metrics Engine/i)).toBeInTheDocument();
    expect(screen.getByText(/Continuous Governance Red-Line Gates/i)).toBeInTheDocument();
    expect(screen.getByText(/RL-1:/i)).toBeInTheDocument();
    expect(screen.getByText(/RL-7:/i)).toBeInTheDocument();
  });
});
