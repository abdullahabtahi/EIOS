import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { OperationsBoardView } from '@/components/cockpit/workstations/operations-board';

describe('Operations Board (User Story 5)', () => {
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
