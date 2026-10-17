import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';
import { normalizePersonaRole } from '@/components/cockpit/state/cockpit-types';

describe('Spec-Driven Workstation Tabs and Forensic URL Deserialization', () => {
  it('strictly normalizes role strings and aliases according to domain contracts', () => {
    // Partner Manager variants
    expect(normalizePersonaRole('partner_')).toBe('partner_manager');
    expect(normalizePersonaRole('partner')).toBe('partner_manager');
    expect(normalizePersonaRole('PARTNER_MANAGER')).toBe('partner_manager');
    expect(normalizePersonaRole('partner-manager')).toBe('partner_manager');
    expect(normalizePersonaRole('affiliate')).toBe('partner_manager');

    // Executive variants
    expect(normalizePersonaRole('executive')).toBe('executive');
    expect(normalizePersonaRole('EXECUTIVE')).toBe('executive');
    expect(normalizePersonaRole('exec')).toBe('executive');

    // AML variants
    expect(normalizePersonaRole('aml')).toBe('aml_investigator');
    expect(normalizePersonaRole('aml_')).toBe('aml_investigator');
    expect(normalizePersonaRole('AML_INVESTIGATOR')).toBe('aml_investigator');
    expect(normalizePersonaRole('investigator')).toBe('aml_investigator');

    // Compliance variants
    expect(normalizePersonaRole('compliance')).toBe('compliance_auditor');
    expect(normalizePersonaRole('audit')).toBe('compliance_auditor');
    expect(normalizePersonaRole('COMPLIANCE_AUDITOR')).toBe('compliance_auditor');

    // Data Operations variants
    expect(normalizePersonaRole('data')).toBe('data_operations');
    expect(normalizePersonaRole('data_platform')).toBe('data_operations');
    expect(normalizePersonaRole('DATA_OPERATIONS')).toBe('data_operations');
    expect(normalizePersonaRole('operations')).toBe('data_operations');

    // Invalid values
    expect(normalizePersonaRole('random_gibberish')).toBeNull();
    expect(normalizePersonaRole(null)).toBeNull();
    expect(normalizePersonaRole(undefined)).toBeNull();
  });

  it('allows clicking all 5 workstation tabs without errors and mounts corresponding views', async () => {
    render(
      <CockpitProvider>
        <TripartiteShell />
      </CockpitProvider>
    );

    // Initial state: Executive
    const execTab = screen.getByTestId('tab-executive');
    expect(execTab).toHaveAttribute('aria-selected', 'true');

    // 1. Click Partner Manager tab
    const partnerTab = screen.getByTestId('tab-partner_manager');
    fireEvent.click(partnerTab);
    expect(partnerTab).toHaveAttribute('aria-selected', 'true');
    expect(execTab).toHaveAttribute('aria-selected', 'false');

    // Verify Partner Workstation elements render
    await waitFor(() => {
      expect(screen.getAllByText(/Partner Disengagement Radar/i)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/Gemini 3.8 Flash/i)[0]).toBeInTheDocument();
    });

    // 2. Click AML Investigator tab
    const amlTab = screen.getByTestId('tab-aml_investigator');
    fireEvent.click(amlTab);
    expect(amlTab).toHaveAttribute('aria-selected', 'true');
    expect(partnerTab).toHaveAttribute('aria-selected', 'false');

    // 3. Click Compliance & Audit tab
    const compTab = screen.getByTestId('tab-compliance_auditor');
    fireEvent.click(compTab);
    expect(compTab).toHaveAttribute('aria-selected', 'true');

    // 4. Click Data Operations tab
    const dataTab = screen.getByTestId('tab-data_operations');
    fireEvent.click(dataTab);
    expect(dataTab).toHaveAttribute('aria-selected', 'true');

    // 5. Click back to Executive tab
    fireEvent.click(execTab);
    expect(execTab).toHaveAttribute('aria-selected', 'true');
  });

  it('deserializes malformed URL search params (e.g. role=partner_) into Partner Manager', async () => {
    // Simulate window.location.search having ?role=partner_
    const originalSearch = window.location.search;
    delete (window as any).location;
    window.location = {
      ...window.location,
      search: '?role=partner_&entityId=AP-1029',
      pathname: '/cockpit',
      href: 'http://localhost:3000/cockpit?role=partner_&entityId=AP-1029',
    } as any;

    render(
      <CockpitProvider>
        <TripartiteShell />
      </CockpitProvider>
    );

    // Should immediately normalize role=partner_ to partner_manager
    const partnerTab = screen.getByTestId('tab-partner_manager');
    expect(partnerTab).toHaveAttribute('aria-selected', 'true');

    await waitFor(() => {
      expect(screen.getAllByText(/Gemini 3.8 Flash/i)[0]).toBeInTheDocument();
    });

    window.location.search = originalSearch;
  });
});
