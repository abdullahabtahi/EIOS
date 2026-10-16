import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import { getPipelineStatus } from '@/components/cockpit/state/pipeline-status';
import type { PersonaRole, WorkstationApiResponse } from '@/components/cockpit/state/cockpit-types';

const liveFor = (role: PersonaRole, marker: string): WorkstationApiResponse => {
  const base = getMockWorkstationState(role);
  return {
    ...base,
    isLiveConnected: true,
    isCachedFallback: false,
    triageItems: base.triageItems.map((t, i) => (i === 0 ? { ...t, title: marker } : t)),
  };
};

function Probe() {
  const { state, setRole, refreshWorkstation } = useCockpit();
  return (
    <>
      <span data-testid="title">{state.triageItems[0]?.title}</span>
      <span data-testid="loading">{String(state.isLoading)}</span>
      <span data-testid="error">{state.error}</span>
      <button type="button" data-testid="refresh" onClick={() => void refreshWorkstation()} />
      <span data-testid="status">{getPipelineStatus(state).label}</span>
      <button type="button" data-testid="go-aml" onClick={() => setRole('aml_investigator')} />
      <button type="button" data-testid="go-exec" onClick={() => setRole('executive')} />
    </>
  );
}

describe('Workstation switching: stale-while-revalidate', () => {
  let behaviour: Record<string, 'live' | 'fail' | 'hang' | 'denied'>;
  let calls: string[];
  let shelfMode: 'live' | 'fail';

  beforeEach(() => {
    behaviour = { executive: 'live', aml_investigator: 'live' };
    calls = [];
    shelfMode = 'live';
    global.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      calls.push(url);
      if (url.startsWith('/api/cockpit/shelf')) {
        if (shelfMode === 'fail') return Promise.reject(new TypeError('network'));
        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ stagedActionCards: [] }) });
      }
      const role = url.split('/').pop()!.split('?')[0] as PersonaRole;
      const mode = behaviour[role];
      if (mode === 'hang') {
        return new Promise((_, reject) =>
          init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))),
        );
      }
      if (mode === 'denied') return Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve({}) });
      if (mode === 'fail') return Promise.reject(new TypeError('network'));
      const marker = `${role}-${calls.length}`;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(liveFor(role, marker)) });
    }) as unknown as typeof fetch;
  });

  afterEach(() => vi.restoreAllMocks());

  const mount = () => render(<CockpitProvider><Probe /></CockpitProvider>);
  // The panels' 30 s TTL: age every cached answer past it.
  const ageCache = () => {
    const real = Date.now();
    vi.spyOn(Date, 'now').mockReturnValue(real + 31_000);
  };
  const click = (id: string) => act(async () => { screen.getByTestId(id).click(); });

  it('shows the last live data at once on switching back, then refreshes behind it', async () => {
    mount();
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/));
    await click('go-aml');
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^aml_investigator-/));

    behaviour.executive = 'hang';
    ageCache();
    await click('go-exec');
    // Not loading, and showing the earlier live executive answer while the refresh hangs.
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/);
    expect(screen.getByTestId('status')).toHaveTextContent('Syncing');
  });

  it('keeps the last live data, labelled Stale, when the refresh fails twice', async () => {
    mount();
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/));
    await click('go-aml');
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^aml_investigator-/));

    behaviour.executive = 'fail';
    ageCache();
    await click('go-exec');
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('Stale'));
    expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/);
    expect(calls.filter((c) => c.includes('executive')).some((c) => c.includes('patient=1'))).toBe(true);
  });

  it('inside the TTL a switch shows the cached panels, refetches no panels and always refetches the shelf', async () => {
    mount();
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/));
    await click('go-aml');
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^aml_investigator-/));
    const before = { exec: calls.filter((c) => c.split('?')[0].endsWith('/executive')).length, shelf: calls.filter((c) => c.includes('/shelf')).length };
    await click('go-exec');
    await waitFor(() => expect(calls.filter((c) => c.includes('/shelf')).length).toBe(before.shelf + 1));
    expect(calls.filter((c) => c.split('?')[0].endsWith('/executive')).length).toBe(before.exec);
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('status')).not.toHaveTextContent('Syncing');
  });

  it('labels the data Stale when only the shelf refresh fails', async () => {
    mount();
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/));
    await click('go-aml');
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^aml_investigator-/));
    shelfMode = 'fail';
    await click('go-exec');
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('Stale'));
  });

  it('keeps the live data, labelled Stale, when a refresh of the same workstation fails', async () => {
    mount();
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/));
    behaviour.executive = 'fail';
    await act(async () => { screen.getByTestId('refresh').click(); });
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('Stale'));
    expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/);
  });

  it('never masks a refused token with a replay or cached data', async () => {
    mount();
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/));
    behaviour.executive = 'denied';
    await act(async () => { screen.getByTestId('refresh').click(); });
    await waitFor(() => expect(screen.getByTestId('error')).not.toBeEmptyDOMElement());
    expect(screen.getByTestId('status')).not.toHaveTextContent('Replay');
  });

  it('warms the other workstations once the visible one is live, so the first switch is instant', async () => {
    mount();
    await waitFor(() => expect(screen.getByTestId('title')).toHaveTextContent(/^executive-/));
    await waitFor(
      () => expect(new Set(calls.filter((c) => !c.includes('/shelf')).map((c) => c.split('?')[0].split('/').pop()))).toEqual(
        new Set(['executive', 'aml_investigator', 'partner_manager', 'compliance_auditor', 'data_operations']),
      ),
      { timeout: 4000 },
    );
    behaviour.aml_investigator = 'hang';
    await click('go-aml');
    expect(screen.getByTestId('loading')).toHaveTextContent('false');
    expect(screen.getByTestId('title')).toHaveTextContent(/^aml_investigator-/);
  });

  it('does not warm anything while the backend is not answering live', async () => {
    behaviour.executive = 'fail';
    mount();
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('Replay'));
    const before = calls.length;
    await new Promise((r) => setTimeout(r, 1300));
    expect(calls.length).toBe(before);
  });

  it('falls back to the labelled replay when there is nothing live to keep', async () => {
    behaviour.executive = 'fail';
    mount();
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('Replay'));
  });
});
