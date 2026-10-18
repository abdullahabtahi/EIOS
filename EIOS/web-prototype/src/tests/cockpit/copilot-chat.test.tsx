import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { DossierColumn } from '@/components/cockpit/shell/dossier-column';
import { GovernedActionShelf } from '@/components/cockpit/shell/governed-action-shelf';

const triage = (entityId: string, title: string, entityType = 'PARTNER') => ({
  id: `t-${entityId}`,
  role: 'partner_manager',
  title,
  subtitle: 'High value, high risk',
  entityId,
  entityType,
  priorityScore: 0.9,
  severity: 'CRITICAL',
  status: 'NEW',
  timestamp: '2026-10-14T00:00:00Z',
  tags: [],
  metricsSummary: {},
});

const workstationBody = {
  workstation: 'partner_manager',
  isLiveConnected: true,
  isCachedFallback: false,
  asOfTimestamp: '2026-10-10T10:00:00Z',
  session: { sessionId: 'test', systemLatencyMs: 12 },
  triageItems: [triage('PTR-723', 'Saigon FX Syndicate'), triage('PTR-882', 'Alpha FX LatAm Master')],
  activeDossier: null,
  stagedActionCards: [],
};

const answer = (text: string) => ({
  queryId: 'q',
  naturalLanguageQuery: 'q',
  responseMarkdown: text,
  citedMetrics: [],
  assistantStatus: 'ASSEMBLED',
  dataOrigin: 'fixture',
  steps: [],
  proposals: [],
  timestamp: '2026-10-14T03:57:10Z',
});

function mockBackend(reply: () => Promise<unknown>) {
  const fn = vi.fn().mockImplementation((url: string) =>
    url.includes('/api/cockpit/copilot/query')
      ? reply()
      : Promise.resolve({ ok: true, json: () => Promise.resolve(workstationBody) }),
  );
  global.fetch = fn as unknown as typeof fetch;
  return fn;
}
const ok = (body: unknown) => () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });

function Controls() {
  const { selectEntity, setRole } = useCockpit();
  return (
    <>
      <button onClick={() => selectEntity('PTR-723')}>select-723</button>
      <button onClick={() => selectEntity('PTR-882')}>select-882</button>
      <button onClick={() => setRole('executive')}>role-executive</button>
      <button onClick={() => setRole('partner_manager')}>role-partner</button>
    </>
  );
}

async function renderColumn() {
  render(
    <CockpitProvider>
      <DossierColumn />
      <GovernedActionShelf />
      <Controls />
    </CockpitProvider>,
  );
  fireEvent.click(screen.getByText('role-partner'));
  await waitFor(() => expect(global.fetch).toHaveBeenCalled());
}

const send = (text: string) => {
  const input = screen.getByLabelText('Ask the copilot');
  fireEvent.change(input, { target: { value: text } });
  fireEvent.submit(input.closest('form')!);
};

afterEach(() => vi.restoreAllMocks());

describe('the dossier column switch', () => {
  it('shows the dossier first and the chat after the Chat tab is chosen, keeping both mounted', async () => {
    mockBackend(ok(answer('hi')));
    await renderColumn();
    expect(screen.getByRole('tab', { name: 'Dossier' })).toHaveAttribute('aria-selected', 'true');
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    expect(screen.getByRole('tab', { name: /Chat/ })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByLabelText('Ask the copilot')).toBeInTheDocument();
  });

  it('keeps a typed question when the operator flips to the dossier and back', async () => {
    mockBackend(ok(answer('hi')));
    await renderColumn();
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    fireEvent.change(screen.getByLabelText('Ask the copilot'), { target: { value: 'half typed' } });
    fireEvent.click(screen.getByRole('tab', { name: 'Dossier' }));
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    expect(screen.getByLabelText('Ask the copilot')).toHaveValue('half typed');
  });

  it('puts a dot on the Chat tab when an answer arrives while the dossier is showing, and clears it on opening', async () => {
    let release: ((v: unknown) => void) | undefined;
    mockBackend(() => new Promise((r) => (release = r)));
    await renderColumn();
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    send('hello');
    await waitFor(() => expect(release).toBeDefined());
    fireEvent.click(screen.getByRole('tab', { name: 'Dossier' }));
    await act(async () => release!({ ok: true, status: 200, json: () => Promise.resolve(answer('Hello there')) }));
    expect(await screen.findByTestId('chat-unread')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    expect(screen.queryByTestId('chat-unread')).not.toBeInTheDocument();
    expect(screen.getByText('Hello there')).toBeInTheDocument();
  });
});

describe('the chat view', () => {
  it('shows the entity on screen in a context strip and suggests questions about it', async () => {
    mockBackend(ok(answer('hi')));
    await renderColumn();
    await waitFor(() => fireEvent.click(screen.getByText('select-723')));
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    expect(screen.getByTestId('chat-context')).toHaveTextContent('PTR-723');
    expect(screen.getByTestId('chat-context')).toHaveTextContent('Saigon FX Syndicate');
    expect(screen.getByRole('button', { name: 'Why is PTR-723 at risk?' })).toBeInTheDocument();
  });

  it('sends a clicked suggestion with the entity on screen', async () => {
    const fetchMock = mockBackend(ok(answer('Because of a rival bounty.')));
    await renderColumn();
    await waitFor(() => fireEvent.click(screen.getByText('select-723')));
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Why is PTR-723 at risk?' }));
    expect(await screen.findByText('Because of a rival bounty.')).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([url]) => String(url).includes('/copilot/query'))!;
    expect(JSON.parse(call[1].body)).toMatchObject({ query: 'Why is PTR-723 at risk?', activeEntityId: 'PTR-723', role: 'partner_manager' });
  });

  it('marks where the entity on screen changed between two questions', async () => {
    mockBackend(ok(answer('An answer.')));
    await renderColumn();
    await waitFor(() => fireEvent.click(screen.getByText('select-723')));
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    send('first');
    await screen.findByText('An answer.');
    fireEvent.click(screen.getByText('select-882'));
    send('second');
    expect(await screen.findByRole('separator')).toHaveTextContent('Now viewing PTR-882');
  });

  it('keeps a separate thread for each workstation and clears only the one being shown', async () => {
    mockBackend(ok(answer('Partner answer.')));
    await renderColumn();
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    send('partner question');
    await screen.findByText('Partner answer.');
    fireEvent.click(screen.getByText('role-executive'));
    expect(screen.queryByText('Partner answer.')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('role-partner'));
    expect(await screen.findByText('Partner answer.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Clear conversation' }));
    expect(screen.queryByText('Partner answer.')).not.toBeInTheDocument();
  });

  it('offers Show in dossier on an answer about an entity and goes back to the dossier', async () => {
    mockBackend(ok(answer('About this partner.')));
    await renderColumn();
    await waitFor(() => fireEvent.click(screen.getByText('select-723')));
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    send('brief');
    fireEvent.click(await screen.findByRole('button', { name: /Show in dossier/i }));
    expect(screen.getByRole('tab', { name: 'Dossier' })).toHaveAttribute('aria-selected', 'true');
  });

  it('folds the badges of a long list behind a disclosure, but shows a few figures directly', async () => {
    const figure = (i: number) => ({
      metricId: `alerts[${i}].risk_score`,
      name: 'risk score',
      rawValue: i,
      formattedValue: `${80 + i}`,
      unit: 'score',
      semanticDefinitionVersion: '',
      asOfTimestamp: '2026-10-14T03:57:10+00:00',
      originEngine: 'port.alerts',
      stewardRole: 'port.alerts',
      citation: '[ILLUSTRATIVE]',
      isCached: false,
      dataOrigin: 'fixture',
    });
    mockBackend(ok({ ...answer('Many alerts.'), citedMetrics: [0, 1, 2, 3, 4, 5].map(figure) }));
    await renderColumn();
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    send('alerts');
    const summary = await screen.findByText('Sources for 6 figures');
    expect(summary.closest('details')).not.toHaveAttribute('open');

    mockBackend(ok({ ...answer('Few alerts.'), citedMetrics: [0, 1].map(figure) }));
    send('one more');
    await screen.findByText('Few alerts.');
    expect(screen.queryByText('Sources for 2 figures')).not.toBeInTheDocument();
  });
});

describe('the model choice', () => {
  const models = [
    { key: 'fast', label: '3.5 Flash-Lite', note: 'Fastest answers', default: true },
    { key: 'deep', label: '3.8 Flash', note: 'All-around help', default: false },
  ];
  const bodies = () =>
    (global.fetch as ReturnType<typeof vi.fn>).mock.calls
      .filter(([url]) => String(url).includes('/api/cockpit/copilot/query'))
      .map(([, init]) => JSON.parse(String((init as RequestInit).body)));

  it('asks on the default model, and on the one the operator picks after that', async () => {
    const fn = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/copilot/models')) return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ models }) });
      if (url.includes('/copilot/query')) return ok(answer('hi'))();
      return Promise.resolve({ ok: true, json: () => Promise.resolve(workstationBody) });
    });
    global.fetch = fn as unknown as typeof fetch;
    window.localStorage.clear();
    await renderColumn();
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    await screen.findByRole('button', { name: /^Model/ });
    send('first');
    await waitFor(() => expect(bodies()).toHaveLength(1));
    expect(bodies()[0].model).toBe('fast');
    await screen.findByText('hi');
    fireEvent.click(screen.getByRole('button', { name: /^Model/ }));
    fireEvent.click(screen.getByRole('option', { name: /deep|All-around|3.8/i }));
    send('second');
    await waitFor(() => expect(bodies()).toHaveLength(2));
    expect(bodies()[1].model).toBe('deep');
    window.localStorage.clear();
  });

  it('names no model when the list could not be read', async () => {
    mockBackend(ok(answer('hi')));
    await renderColumn();
    fireEvent.click(screen.getByRole('tab', { name: /Chat/ }));
    send('first');
    await waitFor(() => expect(bodies()).toHaveLength(1));
    expect(bodies()[0]).not.toHaveProperty('model');
  });
});
