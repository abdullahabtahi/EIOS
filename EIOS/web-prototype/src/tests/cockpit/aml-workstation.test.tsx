import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { AmlWorkstationView } from '@/components/cockpit/workstations/aml-workstation';

describe('AML Investigator Workstation (User Story 3)', () => {
  it('renders one-screen evidence dossier with KYC turnover velocity and hardware fingerprint', () => {
    render(
      <CockpitProvider>
        <AmlWorkstationView />
      </CockpitProvider>
    );

    expect(screen.getAllByText(/ACC-88219/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/\$1,420,000/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/3.8x Ratio/i)).toBeInTheDocument();
    expect(screen.getAllByText(/DEV-F89A/i)[0]).toBeInTheDocument();
  });

  it('toggles dynamic CGNAT hub suppression', () => {
    render(
      <CockpitProvider>
        <AmlWorkstationView />
      </CockpitProvider>
    );

    const toggleBtn = screen.getByRole('button', { name: /CGNAT Suppressed/i });
    expect(toggleBtn).toBeInTheDocument();

    fireEvent.click(toggleBtn);
    expect(screen.getByText(/Show Full Hairball/i)).toBeInTheDocument();
  });

  it('edits SAR draft narrative and stages official SAR filing', () => {
    render(
      <CockpitProvider>
        <AmlWorkstationView />
      </CockpitProvider>
    );

    const textarea = screen.getByLabelText(/Suspicious Activity Description/i);
    expect(textarea).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: 'Updated FinCEN narrative with confirmed mirror trades.' } });

    const stageBtn = screen.getByRole('button', { name: /Stage Official SAR Filing/i });
    fireEvent.click(stageBtn);

    // Staged into Governed Action Shelf
    expect(screen.getByText(/Save Draft Narrative/i)).toBeInTheDocument();
  });
});
