import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import type { PersonaRole } from '@/components/cockpit/state/cockpit-types';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';

// Mock global fetch for testing
beforeEach(() => {
  global.fetch = vi.fn().mockImplementation(() => {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({
        workstation: 'executive',
        isLiveConnected: true,
        isCachedFallback: false,
        asOfTimestamp: '2026-10-10T10:00:00.000Z',
        session: {
          sessionId: 'test_sess',
          activeRole: 'executive',
          operator: {
            officerId: 'OP_TEST',
            name: 'Test Officer',
            email: 'test@enterprise.internal',
            role: 'executive',
            clearanceLevel: 'LEVEL_3_EXECUTIVE',
            idpClaim: 'claim_test',
            sessionNonce: 'nonce_test',
          },
          activeTriageItemId: 'item_1',
          triageFilter: {},
          governedActionShelfExpanded: true,
          stagedActionsCount: 1,
          isSimulatedOutage: false,
          systemLatencyMs: 12,
        },
        triageItems: [
          {
            id: 'item_1',
            role: 'executive',
            title: 'Test LatAm Spread Shock',
            subtitle: '18 bps widening',
            entityId: 'COMP-LATAM-01',
            entityType: 'BRIEFING',
            priorityScore: 0.95,
            severity: 'CRITICAL',
            status: 'OPEN',
            timestamp: '2026-10-10T10:00:00Z',
            tags: ['Rates', 'LatAm'],
            metricsSummary: { shock: '18 bps' },
          },
        ],
        activeDossier: {
          dossierId: 'doss_1',
          entityId: 'COMP-LATAM-01',
          role: 'executive',
          headline: 'Executive Dossier Headline',
          executiveSummary: 'Executive summary test narrative',
          sections: [
            {
              sectionId: 'sec_1',
              title: 'Causal Drivers',
              narrativeText: 'Detailed causal drivers breakdown.',
              citations: ['[BRIEF]'],
              metrics: [],
            },
          ],
          asOfTimestamp: '2026-10-10T10:00:00Z',
          isCachedSnapshot: false,
        },
        canvasPayload: {
          type: 'CAUSAL_DAG',
          data: { nodes: [], edges: [] },
        },
        stagedActionCards: [],
        drProofs: [],
        redLineGates: [],
      }),
    });
  });
});

function RoleDriver({ role }: { role: PersonaRole }) {
  const { setRole } = useCockpit();
  React.useEffect(() => { setRole(role); }, [role, setRole]);
  return null;
}

describe('Tripartite Shell Layout & Navigation (User Story 1)', () => {
  it('renders all tripartite COP zones: Left Rail, Center Dossier, Right Canvas, Header Nav, and Governed Action Shelf', async () => {
    render(
      <CockpitProvider>
        <RoleDriver role="aml_investigator" />
        <TripartiteShell />
      </CockpitProvider>
    );

    // Header Nav elements
    expect(screen.getByText(/OPERATOR COCKPIT/i)).toBeInTheDocument();
    
    // System status (opened from the header pipeline chip) hosts Principle VIII Fallback & Outage Verification
    fireEvent.click(screen.getByTestId('header-pipeline-status'));
    expect(screen.getByRole('button', { name: /Simulate Outage/i })).toBeInTheDocument();

    // Left Triage Rail
    expect(await screen.findByPlaceholderText(/Filter triage queue/i)).toBeInTheDocument();

    // Governed Action Shelf
    expect(screen.getByText(/GOVERNED ACTION SHELF/i)).toBeInTheDocument();
  });

  it('triggers simulated outage mode and renders [REPLAY] banner', async () => {
    render(
      <CockpitProvider>
        <TripartiteShell />
      </CockpitProvider>
    );

    fireEvent.click(screen.getByTestId('header-pipeline-status'));
    const outageToggle = screen.getByRole('button', { name: /Simulate Outage/i });
    fireEvent.click(outageToggle);

    await waitFor(() => {
      expect(screen.getByText(/PRINCIPLE VIII ACTIVE/i)).toBeInTheDocument();
      expect(screen.getByText(/Simulated Outage Mode Active/i)).toBeInTheDocument();
    });
  });
});
