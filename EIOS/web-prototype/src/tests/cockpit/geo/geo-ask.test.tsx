import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { clearGeoChat } from '@/components/cockpit/geo/geo-chat-store';

const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { GeoAsk } from '@/components/cockpit/geo/geo-ask';

const ANSWER = {
  queryId: 'q1',
  naturalLanguageQuery: 'why?',
  responseMarkdown: 'The exit in Nigeria is shared by 22 accounts.',
  citedMetrics: [],
  assistantStatus: 'ASSEMBLED',
  blocked: false,
  steps: ['get_shared_exit'],
  proposals: [],
  viewCommands: [
    { kind: 'gateway', id: 'GW-NG-X00' },
    { kind: 'account', id: 'CR11568' },
  ],
  turnLatencyMs: 2140,
  timestamp: '2026-10-16T00:00:00Z',
};

function reply(status: number, body: unknown) {
  authFetch.mockImplementation(async (url: string) =>
    url.includes('/copilot/models')
      ? { ok: true, status: 200, json: async () => ({ models: [] }) }
      : { ok: status < 400, status, json: async () => body },
  );
}

const CONTEXT = { view: 'logins' as const, selection: { kind: 'gateway' as const, id: 'GW-NG-X00' } };

beforeEach(() => {
  clearGeoChat();
  authFetch.mockReset(); // a block body: a returned function would be run as a cleanup hook
});

describe('the geospatial assistant beside the map', () => {
  it('asks with the map context and applies the first move when the answer arrives', async () => {
    reply(200, ANSWER);
    const onMove = vi.fn();
    render(<GeoAsk context={CONTEXT} selected={{ kind: 'gateway', id: 'GW-NG-X00' }} onMove={onMove} />);
    fireEvent.click(screen.getByText('Why is this exit suspicious, and who else is in its ring?'));
    await waitFor(() => expect(onMove).toHaveBeenCalledWith({ kind: 'gateway', id: 'GW-NG-X00' }, true));
    const query = authFetch.mock.calls.find(([url]) => String(url).includes('/copilot/query'))!;
    const body = JSON.parse(query[1].body);
    expect(body).toMatchObject({ role: 'geospatial', mapContext: CONTEXT });
    expect(await screen.findByText(/shared by 22 accounts/)).toBeInTheDocument();
    expect(screen.getByTestId('geo-turn-trace')).toHaveTextContent('Read: shared exit and its ring (BigQuery Graph) · 2.1 s');
  });

  it('keeps every move as a button the reader can press again', async () => {
    reply(200, ANSWER);
    const onMove = vi.fn();
    render(<GeoAsk context={{ view: 'corridors' }} selected={null} onMove={onMove} />);
    fireEvent.change(screen.getByLabelText('Ask the geospatial assistant'), { target: { value: 'Who else?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    fireEvent.click(await screen.findByText('account CR11568'));
    expect(onMove).toHaveBeenLastCalledWith({ kind: 'account', id: 'CR11568' }, false);
  });

  it('says plainly when the assistant is offline and moves nothing', async () => {
    reply(503, { detail: 'offline' });
    const onMove = vi.fn();
    render(<GeoAsk context={{ view: 'corridors' }} selected={null} onMove={onMove} />);
    fireEvent.click(screen.getByText('Where should I look first?'));
    expect(await screen.findByRole('alert')).toHaveTextContent(/offline/i);
    expect(onMove).not.toHaveBeenCalled();
  });

  it('marks where the map selection changed between questions', async () => {
    reply(200, { ...ANSWER, viewCommands: [] });
    const { rerender } = render(<GeoAsk context={{ view: 'corridors' }} selected={null} onMove={vi.fn()} />);
    fireEvent.click(screen.getByText('Where should I look first?'));
    await screen.findByText(/shared by 22 accounts/);
    rerender(<GeoAsk context={CONTEXT} selected={{ kind: 'gateway', id: 'GW-NG-X00' }} onMove={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Ask the geospatial assistant'), { target: { value: 'And this?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(await screen.findByRole('separator')).toHaveTextContent('Now viewing gateway GW-NG-X00');
  });
});

describe('the thread across a workstation switch', () => {
  it('comes back when the panel is mounted again', async () => {
    reply(200, ANSWER);
    const first = render(<GeoAsk context={{ view: 'corridors' }} selected={null} onMove={() => undefined} />);
    fireEvent.click(screen.getByText('Where should I look first?'));
    await screen.findByText(/shared by 22 accounts/);
    first.unmount();
    render(<GeoAsk context={{ view: 'corridors' }} selected={null} onMove={() => undefined} />);
    expect(screen.getByText('Where should I look first?')).toBeInTheDocument();
    expect(screen.getByText(/shared by 22 accounts/)).toBeInTheDocument();
  });
});
