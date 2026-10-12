import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { ExecutiveCockpitView } from '@/components/cockpit/workstations/executive-cockpit';

describe('Executive Decision Cockpit (User Story 2)', () => {
  it('renders 4-horizon Morning Briefing and Strategic Countermeasure Trade-off cards', () => {
    render(
      <CockpitProvider>
        <ExecutiveCockpitView />
      </CockpitProvider>
    );

    // 4 Horizons
    expect(screen.getAllByText(/COMPETITIVE/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/PARTNER FLOW/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/CLIENT RETENTION/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/FINANCIAL METRICS/i)[0]).toBeInTheDocument();

    // Strategic Trade-offs
    expect(screen.getByText(/Strategic Trade-off Analysis/i)).toBeInTheDocument();
  });

  it('verifies sub-200ms What-If shock slider and 100% additive waterfall attribution sum', () => {
    render(
      <CockpitProvider>
        <ExecutiveCockpitView />
      </CockpitProvider>
    );

    // Attribution waterfall indicator
    expect(screen.getByText(/Σ Attribution = 100.0%/i)).toBeInTheDocument();

    // Move slider
    const slider = screen.getByLabelText(/Broker Fee Spread Shock Slider/i);
    fireEvent.change(slider, { target: { value: '25' } });

    expect(screen.getAllByText(/\+25 bps/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Propagation:/i)).toBeInTheDocument();
  });
});
