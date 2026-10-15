import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { ModelPicker, useModelChoice } from '@/components/cockpit/shell/model-picker';

const MODELS = [
  { key: 'fast', label: '3.5 Flash-Lite', note: 'Fastest answers', default: true },
  { key: 'deep', label: '3.8 Flash', note: 'All-around help', default: false },
];

function Harness() {
  const m = useModelChoice();
  return (
    <>
      <ModelPicker choices={m.choices} selected={m.selected} onSelect={m.select} />
      <output data-testid="selected">{m.selected ?? 'none'}</output>
    </>
  );
}

const respond = (body: unknown, ok = true) => {
  global.fetch = vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 503, json: () => Promise.resolve(body) }) as unknown as typeof fetch;
};

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
});

describe('model picker', () => {
  it('starts on the backend default, the fastest model', async () => {
    respond({ models: MODELS });
    render(<Harness />);
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Model' })).toBeTruthy());
    expect(screen.getByTestId('selected').textContent).toBe('fast');
  });

  it('remembers the operator pick for next time', async () => {
    respond({ models: MODELS });
    render(<Harness />);
    const select = await screen.findByRole('combobox', { name: 'Model' });
    act(() => {
      fireEvent.change(select, { target: { value: 'deep' } });
    });
    expect(screen.getByTestId('selected').textContent).toBe('deep');
    expect(window.localStorage.getItem('eios.copilot.model')).toBe('deep');
  });

  it('ignores a remembered model the backend no longer offers', async () => {
    window.localStorage.setItem('eios.copilot.model', 'retired');
    respond({ models: MODELS });
    render(<Harness />);
    await waitFor(() => expect(screen.getByTestId('selected').textContent).toBe('fast'));
  });

  it('shows nothing and names no model when the list cannot be read', async () => {
    respond({ detail: 'offline' }, false);
    render(<Harness />);
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByRole('combobox')).toBeNull();
    expect(screen.getByTestId('selected').textContent).toBe('none');
  });

  it('shows nothing for a body that is not a model list', async () => {
    respond({ workstation: 'partner_manager' });
    render(<Harness />);
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByRole('combobox')).toBeNull();
  });
});
