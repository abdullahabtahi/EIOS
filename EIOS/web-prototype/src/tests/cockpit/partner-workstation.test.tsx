import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { PartnerWorkstationView } from '@/components/cockpit/workstations/partner-workstation';
import { PartnerTriageGrid } from '@/components/cockpit/common/partner-triage-grid';
import { MOCK_PARTNERS } from '@/components/cockpit/common/churn-radar-scatter';

describe('Partner Manager Workstation (Production Hardening US1-US5)', () => {
  it('renders the Disengagement Radar with risk score x VaR quadrants and historical drift trajectories', () => {
    render(
      <CockpitProvider>
        <PartnerWorkstationView />
      </CockpitProvider>
    );

    expect(screen.getAllByText(/PTR-882/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/HIGH VALUE \/ HIGH DISENGAGEMENT RISK/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Disengagement risk score/i)[0]).toBeInTheDocument();
    expect(screen.getByTestId('partner-triage-grid')).toBeInTheDocument();
    // The score detects disengagement under way; it is not a forecast, so no label calls it a churn probability.
    expect(screen.queryByText(/P\(churn\)/)).not.toBeInTheDocument();
  });

  it('filters and sorts high-density partner triage grid with search query', () => {
    const handleSelect = vi.fn();
    render(
      <PartnerTriageGrid
        partners={MOCK_PARTNERS}
        selectedPartnerId="PTR-882"
        onSelectPartner={handleSelect}
      />
    );

    // Initial partner count
    expect(screen.getByText(/SHOWING/i)).toHaveTextContent(`SHOWING 20 / 20`);

    // Search for Colombia / LatAm
    const searchInput = screen.getByRole('searchbox');
    fireEvent.change(searchInput, { target: { value: 'Colombia' } });

    // Should filter to Colombia partners
    expect(screen.getByTestId('triage-row-PTR-882')).toBeInTheDocument();
    expect(screen.queryByTestId('triage-row-PTR-104')).not.toBeInTheDocument();

    // Clicking a row dispatches onSelectPartner
    fireEvent.click(screen.getByTestId('triage-row-PTR-882'));
    expect(handleSelect).toHaveBeenCalledWith(expect.objectContaining({ partnerId: 'PTR-882' }));
  });
});
