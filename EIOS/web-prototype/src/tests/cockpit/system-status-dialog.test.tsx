import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import type { PersonaRole } from '@/components/cockpit/state/cockpit-types';
import { HeaderNav } from '@/components/cockpit/shell/header-nav';
import { TripartiteShell } from '@/components/cockpit/shell/tripartite-shell';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';

function mockLive() {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ ...getMockWorkstationState('executive'), dataOrigin: 'live' }),
  }) as unknown as typeof fetch;
}

function mockFixture() {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ ...getMockWorkstationState('executive'), dataOrigin: 'fixture' }),
  }) as unknown as typeof fetch;
}

afterEach(() => vi.restoreAllMocks());

function RoleDriver({ role }: { role: PersonaRole }) {
  const { setRole } = useCockpit();
  React.useEffect(() => { setRole(role); }, [role, setRole]);
  return null;
}

describe('System status dialog (replaces the canvas "Diagnostics" tab)', () => {
  it('opens from the header pipeline chip, which is a real button with dialog semantics', async () => {
    mockLive();
    render(
      <CockpitProvider>
        <HeaderNav />
      </CockpitProvider>,
    );
    const chip = screen.getByTestId('header-pipeline-status');
    expect(chip.tagName).toBe('BUTTON');
    expect(chip).toHaveAttribute('aria-haspopup', 'dialog');
    fireEvent.click(chip);
    const dialog = await screen.findByRole('dialog', { name: /System status/i });
    expect(within(dialog).getByText(/Pipeline/i)).toBeInTheDocument();
  });

  it('shows derived pipeline status, red-line gates labelled illustrative, and "—" for missing flywheel data', async () => {
    mockLive();
    render(
      <CockpitProvider>
        <HeaderNav />
      </CockpitProvider>,
    );
    fireEvent.click(screen.getByTestId('header-pipeline-status'));
    const dialog = await screen.findByRole('dialog', { name: /System status/i });
    await waitFor(() => expect(within(dialog).getByTestId('status-pipeline')).toHaveTextContent(/Live/));
    expect(within(dialog).getByText(/\[ILLUSTRATIVE\]/)).toBeInTheDocument();
    expect(within(dialog).getAllByText(/RL-\d/).length).toBeGreaterThan(0);
  });

  it('says Fixture, never Live, when the connection is up but the data is a fixture', async () => {
    mockFixture();
    render(
      <CockpitProvider>
        <HeaderNav />
      </CockpitProvider>,
    );
    await waitFor(() => expect(screen.getByTestId('header-pipeline-status')).toHaveTextContent(/Fixture/));
    expect(screen.getByTestId('header-pipeline-status')).not.toHaveTextContent(/Live/);
  });

  it('offers outage simulation and the shell then shows the replay banner', async () => {
    mockLive();
    render(
      <CockpitProvider>
        <TripartiteShell />
      </CockpitProvider>,
    );
    fireEvent.click(screen.getByTestId('header-pipeline-status'));
    fireEvent.click(await screen.findByRole('button', { name: /Simulate Outage/i }));
    await waitFor(() => expect(screen.getByText(/Simulated Outage Mode Active/i)).toBeInTheDocument());
    expect(screen.getByTestId('header-pipeline-status')).toHaveTextContent(/Replay/);
  });
});

describe('Pane collapse controls live inside their pane headers', () => {
  it('triage collapse is inside the triage rail header; canvas collapse inside the canvas bar', async () => {
    window.history.replaceState(null, '', '/'); // an earlier test may have left a role in the address
    mockLive();
    render(
      <CockpitProvider>
        <RoleDriver role="aml_investigator" />
        <TripartiteShell />
      </CockpitProvider>,
    );
    const left = await screen.findByRole('button', { name: /Collapse Left Rail/i });
    expect(left.closest('aside[aria-label="Triage Queue Rail"]')).not.toBeNull();
    const right = screen.getByRole('button', { name: /Collapse Right Canvas/i });
    expect(right.closest('[data-testid="canvas-bar"]')).not.toBeNull();
    fireEvent.click(left);
    expect(screen.getByRole('button', { name: /Expand Left Rail/i })).toBeInTheDocument();
  });
});
