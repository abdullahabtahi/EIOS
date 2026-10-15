import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { CopilotChat } from '@/components/cockpit/shell/copilot-chat';

const workstationBody = {
  workstation: 'executive',
  isLiveConnected: true,
  isCachedFallback: false,
  asOfTimestamp: '2026-10-10T10:00:00Z',
  session: { sessionId: 'test', systemLatencyMs: 12 },
  triageItems: [],
  activeDossier: null,
  stagedActionCards: [],
};

function mockCopilot(reply: () => Promise<unknown>) {
  global.fetch = vi.fn().mockImplementation((url: string) =>
    url.includes('/api/cockpit/copilot/query')
      ? reply()
      : Promise.resolve({ ok: true, json: () => Promise.resolve(workstationBody) }),
  ) as unknown as typeof fetch;
}

async function ask(text: string) {
  render(
    <CockpitProvider>
      <CopilotChat />
    </CockpitProvider>,
  );
  const input = screen.getByLabelText('Ask the copilot');
  fireEvent.change(input, { target: { value: text } });
  fireEvent.submit(input.closest('form')!);
}

afterEach(() => vi.restoreAllMocks());

describe('the copilot chat never fabricates an answer', () => {
  it.each([
    [401, /not authorized/i],
    [403, /not permitted/i],
    [503, /backend is offline/i],
    [500, /HTTP 500/],
  ])('shows an explicit error for HTTP %i and no audit badge', async (status, message) => {
    mockCopilot(() => Promise.resolve({ ok: false, status, json: () => Promise.resolve({ detail: 'nope' }) }));
    await ask('What is the LatAm spread impact?');

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.queryByText(/AUDIT PASSED/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Spread Shock LatAm/i)).not.toBeInTheDocument();
  });

  it('shows an explicit error when the request itself fails', async () => {
    mockCopilot(() => Promise.reject(new TypeError('network down')));
    await ask('anything');
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be reached/i);
    expect(screen.queryByText(/AUDIT PASSED/i)).not.toBeInTheDocument();
  });
});

describe('a rate-limited question', () => {
  it('says so plainly and generates no answer', async () => {
    const { describeCopilotFailure } = await import('@/components/cockpit/shell/copilot-chat');
    const message = describeCopilotFailure(429);
    expect(message).toMatch(/too many questions/i);
    expect(message).toMatch(/no answer was generated/i);
  });
});
