import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { PartnerWorkstationView } from '@/components/cockpit/workstations/partner-workstation';
import { PartnerTriageGrid } from '@/components/cockpit/common/partner-triage-grid';
import { MOCK_PARTNERS } from '@/components/cockpit/common/churn-radar-scatter';

describe('Partner Manager Workstation (Production Hardening US1-US5)', () => {
  it('renders Churn Hazard Radar with P(churn) x VaR quadrants and historical drift trajectories', () => {
    render(
      <CockpitProvider>
        <PartnerWorkstationView />
      </CockpitProvider>
    );

    expect(screen.getAllByText(/PTR-882/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/HIGH VALUE \/ CRITICAL CHURN HAZARD/i)).toBeInTheDocument();
    expect(screen.getAllByText(/P\(churn\) Hazard Rate/i)[0]).toBeInTheDocument();
    expect(screen.getByTestId('partner-triage-grid')).toBeInTheDocument();
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

  it('renders driver-adaptive playbook, What-If simulator, and Experience Library telemetry', async () => {
    render(
      <CockpitProvider>
        <PartnerWorkstationView />
      </CockpitProvider>
    );

    // Experience Library empirical win rate
    expect(screen.getByText(/Empirical Playbook Win Rate:/i)).toBeInTheDocument();
    expect(screen.getByText(/Shadow Model Brier Calibration:/i)).toBeInTheDocument();

    // Driver-Adaptive Playbook
    expect(screen.getByText(/Recommended Driver-Adaptive Playbook/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Stage Governed Action/i })).toBeInTheDocument();

    // What-If Simulator Slider
    const slider = screen.getByLabelText(/Concession Intensity Slider/i);
    fireEvent.change(slider, { target: { value: '70' } });

    await waitFor(() => {
      expect(screen.getByText(/70% Intensity/i)).toBeInTheDocument();
    });
  });

  it('stages 1-click batch cohort remediation in COHORTS view', () => {
    render(
      <CockpitProvider>
        <PartnerWorkstationView />
      </CockpitProvider>
    );

    // Switch to Cohort view
    const cohortToggle = screen.getByRole('button', { name: /^COHORTS/i });
    fireEvent.click(cohortToggle);

    // Verify 1-click batch remediation button appears and is clickable
    const batchBtn = screen.getByRole('button', { name: /1-Click Batch Stage LatAm VIP Cashier Rails/i });
    expect(batchBtn).toBeInTheDocument();
    fireEvent.click(batchBtn);

    // Verify notification toast or staging confirmation
    expect(screen.getByText(/Atomic Cohort Remediation staged/i)).toBeInTheDocument();
  });

  it('renders 3-tier sub-affiliate tree and mirror trading ring alert', () => {
    render(
      <CockpitProvider>
        <PartnerWorkstationView />
      </CockpitProvider>
    );

    expect(screen.getByText(/3-Tier Sub-Affiliate Hierarchy/i)).toBeInTheDocument();
    expect(screen.getByText(/Mirror Trading Ring Detected: 88.0%/i)).toBeInTheDocument();

    const clawbackBtn = screen.getByRole('button', { name: /Stage Commission Clawback/i });
    expect(clawbackBtn).toBeInTheDocument();
    fireEvent.click(clawbackBtn);
  });
});
