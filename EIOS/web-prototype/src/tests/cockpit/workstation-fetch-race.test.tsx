import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import type { PersonaRole, WorkstationApiResponse } from '@/components/cockpit/state/cockpit-types';

interface Deferred {
  role: PersonaRole;
  resolve: (r: WorkstationApiResponse) => void;
  signal?: AbortSignal | null;
}

function respFor(role: PersonaRole, marker: string): WorkstationApiResponse {
  const base = getMockWorkstationState(role);
  return {
    ...base,
    triageItems: base.triageItems.map((t, i) => (i === 0 ? { ...t, title: marker } : t)),
  };
}

function Probe() {
  const { state, setRole, toggleSimulatedOutage } = useCockpit();
  return (
    <>
      <span data-testid="role">{state.activeRole}</span>
      <span data-testid="first-title">{state.triageItems[0]?.title}</span>
      <span data-testid="loading">{String(state.isLoading)}</span>
      <button type="button" data-testid="go-aml" onClick={() => setRole('aml_investigator')} />
      <button type="button" data-testid="go-outage" onClick={() => toggleSimulatedOutage(true)} />
    </>
  );
}

describe('Workstation fetch: stale responses never overwrite the active role', () => {
  let pending: Deferred[];

  beforeEach(() => {
    pending = [];
    global.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      const role = url.split('/').pop() as PersonaRole;
      return new Promise((resolve, reject) => {
        init?.signal?.addEventListener('abort', () =>
          reject(new DOMException('Aborted', 'AbortError')),
        );
        pending.push({
          role,
          signal: init?.signal,
          resolve: (r) => resolve({ ok: true, json: () => Promise.resolve(r) }),
        });
      });
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const flush = () => act(async () => { await Promise.resolve(); });

  it('ignores a slower executive response that lands after the AML response', async () => {
    render(
      <CockpitProvider>
        <Probe />
      </CockpitProvider>,
    );
    await flush();
    // initial executive request is in flight
    expect(pending.map((p) => p.role)).toEqual(['executive']);

    await act(async () => {
      screen.getByTestId('go-aml').click();
    });
    expect(pending.map((p) => p.role)).toEqual(['executive', 'aml_investigator']);

    // AML answers first, then the stale executive answer arrives late
    await act(async () => {
      pending[1].resolve(respFor('aml_investigator', 'AML-ALERT-FRESH'));
    });
    await act(async () => {
      pending[0].resolve(respFor('executive', 'EXEC-STALE'));
    });

    await waitFor(() => expect(screen.getByTestId('first-title')).toHaveTextContent('AML-ALERT-FRESH'));
    expect(screen.getByTestId('role')).toHaveTextContent('aml_investigator');
  });

  it('aborts the superseded request when the role changes', async () => {
    render(
      <CockpitProvider>
        <Probe />
      </CockpitProvider>,
    );
    await flush();
    await act(async () => {
      screen.getByTestId('go-aml').click();
    });
    expect(pending[0].signal?.aborted).toBe(true);
    expect(pending[1].signal?.aborted).toBe(false);
  });

  it('does not let an in-flight live response override a simulated outage snapshot', async () => {
    render(
      <CockpitProvider>
        <Probe />
      </CockpitProvider>,
    );
    await flush();
    await act(async () => {
      screen.getByTestId('go-outage').click();
    });
    await act(async () => {
      pending[0].resolve(respFor('executive', 'LIVE-LATE'));
    });
    await flush();
    expect(screen.getByTestId('first-title')).not.toHaveTextContent('LIVE-LATE');
  });
});
