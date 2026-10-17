import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within, act } from '@testing-library/react';
import React from 'react';
import { FLOWS } from './flows-fixture';
import { REFERENCE } from './reference-fixture';

vi.mock('@vis.gl/react-google-maps', () => ({
  APIProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Map: ({ children }: { children: React.ReactNode }) => <div data-testid="google-map">{children}</div>,
  useMap: () => null,
}));
vi.mock('@deck.gl/google-maps', () => ({
  GoogleMapsOverlay: class {
    setMap = vi.fn();
    setProps = vi.fn();
    finalize = vi.fn();
  },
}));
const authFetch = vi.fn();
vi.mock('@/lib/auth/token', () => ({ authFetch: (...args: unknown[]) => authFetch(...args) }));

import { GeoWorkspace } from '@/components/cockpit/geo/geo-workspace';

const ANSWER = {
  queryId: 'q1', naturalLanguageQuery: 'where?', responseMarkdown: 'Start with Myanmar.', citedMetrics: [], assistantStatus: 'ASSEMBLED',
  blocked: false, steps: [], proposals: [], viewCommands: [], timestamp: '2026-10-16T00:00:00Z',
};
let release: (() => void) | null = null;

function serve({ hold = false }: { hold?: boolean } = {}) {
  authFetch.mockImplementation(async (url: string) => {
    if (url.includes('/copilot/query') && hold) await new Promise<void>((resolve) => (release = resolve));
    const body = url.includes('/geo/reference') ? REFERENCE : url.includes('/geo/flows') ? FLOWS : url.includes('/copilot/models') ? { models: [] } : url.includes('/copilot/query') ? ANSWER : {};
    return { ok: true, status: 200, json: async () => body };
  });
}

const size = { w: Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth'), h: Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientHeight') };
beforeEach(() => {
  window.history.replaceState(null, '', '/');
  window.localStorage.clear();
  authFetch.mockReset();
  release = null;
  serve();
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', { configurable: true, get: () => 1000 });
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', { configurable: true, get: () => 700 });
});
afterEach(() => {
  if (size.w) Object.defineProperty(HTMLElement.prototype, 'clientWidth', size.w);
  if (size.h) Object.defineProperty(HTMLElement.prototype, 'clientHeight', size.h);
});

const launcher = () => screen.getByRole('button', { name: /Ask the assistant/ });
const win = () => screen.getByTestId('geo-chat');
const chat = () => screen.queryByRole('region', { name: 'Ask about the map' });
const input = () => screen.getByRole('textbox', { name: 'Ask the geospatial assistant' }) as HTMLInputElement;

describe('the assistant as a launcher, a window and a docked column', () => {
  it('starts as a launcher alone: no Ask tab on the right, and the right column is the map panel', async () => {
    render(<GeoWorkspace initialSearch="" />);
    expect(launcher()).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Ask' })).toBeNull();
    expect(chat()).toBeNull();
    expect(await screen.findByRole('region', { name: 'Where to look first' })).toBeInTheDocument();
  });

  it('names the map for a screen reader and points at the list as its keyboard route', () => {
    render(<GeoWorkspace initialSearch="" />);
    const map = screen.getByRole('region', { name: 'World map' });
    expect(map).toHaveAccessibleDescription(/Move through what is drawn with the list beside the map/);
  });

  it('titles the window Geospatial Agent whether it floats or is docked; only the floating one shows the grip that says it can be moved', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    expect(within(win()).getByText('Geospatial Agent')).toBeInTheDocument();
    expect(within(win()).getByText('drag_indicator')).toBeInTheDocument();
    expect(within(win()).getByRole('button', { name: 'Move chat window' })).toHaveTextContent('Geospatial Agent');
    fireEvent.click(screen.getByRole('button', { name: 'Dock chat to the left' }));
    expect(within(win()).getByRole('heading', { name: /Geospatial Agent/ })).toBeInTheDocument();
    expect(within(win()).queryByText('drag_indicator')).toBeNull();
  });

  it('keeps the resize corner as an unlabelled-by-icon hit area: named for assistive tech, no glyph drawn', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    const handle = within(win()).getByRole('button', { name: 'Resize chat window' });
    expect(handle).toHaveTextContent('');
  });

  it('opens a floating window from the launcher, and the launcher steps aside', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    expect(chat()).toBeInTheDocument();
    expect(win()).toHaveAttribute('data-mode', 'floating');
    expect(screen.queryByRole('button', { name: /Ask the assistant/ })).toBeNull();
  });

  it('closes back to the launcher without losing what was typed', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    fireEvent.change(input(), { target: { value: 'which exits are new' } });
    fireEvent.click(screen.getByRole('button', { name: 'Close chat' }));
    expect(chat()).toBeNull();
    fireEvent.click(launcher());
    expect(input().value).toBe('which exits are new');
  });

  it('docks to the left and floats again, keeping the same conversation', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    fireEvent.change(input(), { target: { value: 'half a thought' } });
    fireEvent.click(screen.getByRole('button', { name: 'Dock chat to the left' }));
    expect(win()).toHaveAttribute('data-mode', 'docked');
    expect(input().value).toBe('half a thought');
    expect(screen.queryByRole('button', { name: 'Move chat window' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Float chat over the map' }));
    expect(win()).toHaveAttribute('data-mode', 'floating');
    expect(input().value).toBe('half a thought');
  });

  it('puts the docked column before the map in reading order, so it sits at the left', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    fireEvent.click(screen.getByRole('button', { name: 'Dock chat to the left' }));
    const map = screen.getByRole('tab', { name: 'Corridors' });
    expect(win().compareDocumentPosition(map) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('remembers docked or floating, and reopens the same way', () => {
    const first = render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    fireEvent.click(screen.getByRole('button', { name: 'Dock chat to the left' }));
    fireEvent.click(screen.getByRole('button', { name: 'Close chat' }));
    first.unmount();
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    expect(win()).toHaveAttribute('data-mode', 'docked');
  });
});

describe('moving the window', () => {
  it('opens at the bottom right of the map, inside it', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    expect(win()).toHaveStyle({ left: '636px', top: '176px' });
  });

  it('moves with the arrow keys from its handle, further with Shift, and stays inside the map', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    const handle = screen.getByRole('button', { name: 'Move chat window' });
    fireEvent.keyDown(handle, { key: 'ArrowLeft' });
    expect(win()).toHaveStyle({ left: '626px' });
    fireEvent.keyDown(handle, { key: 'ArrowUp', shiftKey: true });
    expect(win()).toHaveStyle({ top: '126px' });
    for (let i = 0; i < 40; i += 1) fireEvent.keyDown(handle, { key: 'ArrowRight', shiftKey: true });
    expect(win()).toHaveStyle({ left: '636px' });
  });

  it('follows the pointer when the handle is dragged, and remembers where it was left', () => {
    const first = render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    const handle = screen.getByRole('button', { name: 'Move chat window' });
    fireEvent.pointerDown(handle, { clientX: 500, clientY: 300, pointerId: 1, button: 0 });
    fireEvent.pointerMove(handle, { clientX: 400, clientY: 250, pointerId: 1 });
    fireEvent.pointerUp(handle, { clientX: 400, clientY: 250, pointerId: 1 });
    expect(win()).toHaveStyle({ left: '536px', top: '126px' });
    first.unmount();
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    expect(win()).toHaveStyle({ left: '536px', top: '126px' });
  });
});

describe('noticing the assistant', () => {
  it('draws the eye with a ring that is there only to be seen once, and not for people who ask for less motion', () => {
    render(<GeoWorkspace initialSearch="" />);
    expect(launcher().querySelector('.geo-ask-ping')).not.toBeNull();
  });

  it('offers a question about what is picked, beside the launcher, and opens with it ready to send', async () => {
    render(<GeoWorkspace initialSearch="?view=corridors&sel=corridor:NO>IR" />);
    const chip = await screen.findByRole('button', { name: /How much money moves on this corridor/ });
    fireEvent.click(chip);
    expect(chat()).toBeInTheDocument();
    expect(input().value).toBe('How much money moves on this corridor, and through whom?');
    expect(authFetch.mock.calls.some(([u]) => String(u).includes('/copilot/query'))).toBe(false);
  });

  it('opens on the slash key and focuses the question, except while typing in a field', () => {
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.keyDown(window, { key: '/' });
    expect(chat()).toBeInTheDocument();
    expect(input()).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Close chat' }));
    const other = document.createElement('input');
    document.body.appendChild(other);
    other.focus();
    fireEvent.keyDown(other, { key: '/' });
    expect(chat()).toBeNull();
    other.remove();
  });

  it('shows that an answer is on its way, and that one is waiting, when the window is closed', async () => {
    serve({ hold: true });
    render(<GeoWorkspace initialSearch="" />);
    fireEvent.click(launcher());
    fireEvent.change(input(), { target: { value: 'where first?' } });
    fireEvent.submit(input().closest('form') as HTMLFormElement);
    fireEvent.click(screen.getByRole('button', { name: 'Close chat' }));
    expect(launcher()).toHaveAttribute('data-status', 'pending');
    await waitFor(() => expect(release).not.toBeNull());
    await act(async () => release?.());
    await waitFor(() => expect(launcher()).toHaveAttribute('data-status', 'unread'));
    fireEvent.click(launcher());
    expect(within(win()).getByText(/Start with Myanmar/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close chat' }));
    expect(launcher()).toHaveAttribute('data-status', 'idle');
  });
});
