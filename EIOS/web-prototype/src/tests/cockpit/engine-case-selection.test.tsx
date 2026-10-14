import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import type { CopilotDossier, PersonaRole, WorkstationApiResponse } from '@/components/cockpit/state/cockpit-types';

const dossierOf = (entityId: string, headline: string): CopilotDossier => ({
  ...getMockWorkstationState('aml_investigator').activeDossier,
  dossierId: `dos_${entityId}`,
  entityId,
  headline,
  sections: [],
});

const engineWorkstation = (): WorkstationApiResponse => {
  const base = getMockWorkstationState('aml_investigator');
  const item = (id: string, entityId: string) => ({ ...base.triageItems[0], id, entityId, title: `AML ${entityId}` });
  return {
    ...base,
    dataOrigin: 'engine',
    triageItems: [item('ALT-CR84920', 'CR84920'), item('ALT-CR91204', 'CR91204')],
    activeDossier: dossierOf('CR84920', 'Computed CR84920'),
  };
};

function Probe() {
  const { state, setRole, selectTriageItem, selectEntity } = useCockpit();
  return (
    <>
      <span data-testid="headline">{state.activeDossier?.headline}</span>
      <span data-testid="status">{state.caseStatus}</span>
      <span data-testid="error">{state.caseError ?? ''}</span>
      <span data-testid="origin">{state.dataOrigin}</span>
      <button type="button" data-testid="go-aml" onClick={() => setRole('aml_investigator' as PersonaRole)} />
      <button type="button" data-testid="pick-91204" onClick={() => selectTriageItem('ALT-CR91204')} />
      <button type="button" data-testid="pick-node" onClick={() => selectEntity('CR00000')} />
    </>
  );
}

describe('Engine-backed AML: selecting a case fetches that account, never a client-side stand-in', () => {
  let calls: string[];

  beforeEach(() => {
    calls = [];
    global.fetch = vi.fn().mockImplementation((url: string) => {
      calls.push(url);
      if (url.includes('/aml/cases/CR91204')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ entityId: 'CR91204', dataOrigin: 'engine', activeDossier: dossierOf('CR91204', 'Computed CR91204'), canvasPayload: null }),
        });
      }
      if (url.includes('/aml/cases/')) return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(engineWorkstation()) });
    }) as unknown as typeof fetch;
  });
  afterEach(() => vi.restoreAllMocks());

  const open = async () => {
    render(
      <CockpitProvider>
        <Probe />
      </CockpitProvider>,
    );
    await act(async () => {
      screen.getByTestId('go-aml').click();
    });
    await waitFor(() => expect(screen.getByTestId('origin')).toHaveTextContent('engine'));
  };

  it('shows the workstation default without a second request', async () => {
    await open();
    expect(screen.getByTestId('headline')).toHaveTextContent('Computed CR84920');
    expect(calls.some((u) => u.includes('/aml/cases/'))).toBe(false);
  });

  it('fetches the computed dossier of the selected alert', async () => {
    await open();
    await act(async () => {
      screen.getByTestId('pick-91204').click();
    });
    await waitFor(() => expect(screen.getByTestId('headline')).toHaveTextContent('Computed CR91204'));
    expect(screen.getByTestId('status')).toHaveTextContent('ready');
    expect(calls.filter((u) => u.includes('/aml/cases/CR91204'))).toHaveLength(1);
  });

  it('says so when an entity has no account record, and keeps the last real dossier', async () => {
    await open();
    await act(async () => {
      screen.getByTestId('pick-node').click();
    });
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('error'));
    expect(screen.getByTestId('error')).toHaveTextContent('No account record for CR00000');
    expect(screen.getByTestId('headline')).toHaveTextContent('Computed CR84920');
  });
});
