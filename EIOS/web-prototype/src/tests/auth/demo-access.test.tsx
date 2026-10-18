import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { parseDemoAccess } from '@/lib/auth/demo-access';
import LoginPage from '@/app/login/page';

vi.mock('next/navigation', () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock('@/lib/auth/auth-context', () => ({ useAuth: () => ({ status: 'signedOut', signIn: vi.fn() }) }));

const VALID = JSON.stringify({
  password: 'judge-demo-2026',
  accounts: [
    { label: 'Analyst', email: 'judge-analyst@eios-demo.example.org' },
    { label: 'Approver 1', email: 'judge-approver1@eios-demo.example.org' },
  ],
});

afterEach(() => vi.restoreAllMocks());

describe('parseDemoAccess', () => {
  it('reads the published accounts and password', () => {
    const access = parseDemoAccess(VALID);
    expect(access?.password).toBe('judge-demo-2026');
    expect(access?.accounts.map((a) => a.label)).toEqual(['Analyst', 'Approver 1']);
  });

  it.each([undefined, null, '', 'not json', '[]', '{}', JSON.stringify({ password: 'x', accounts: [] })])(
    'shows nothing for %j',
    (raw) => expect(parseDemoAccess(raw as string | undefined)).toBeNull(),
  );

  it('refuses an account without a plausible email, or a missing password', () => {
    expect(parseDemoAccess(JSON.stringify({ password: 'p', accounts: [{ label: 'A', email: 'nope' }] }))).toBeNull();
    expect(parseDemoAccess(JSON.stringify({ accounts: [{ label: 'A', email: 'a@b.co' }] }))).toBeNull();
  });
});

describe('the login page', () => {
  it('shows the reviewer card when access is configured, and fills the form from it', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(JSON.parse(VALID)) }) as unknown as typeof fetch;
    render(<LoginPage />);
    expect(await screen.findByTestId('reviewer-access')).toBeInTheDocument();
    expect(screen.getByTestId('reviewer-password')).toHaveTextContent('judge-demo-2026');
    fireEvent.click(screen.getAllByRole('button', { name: /^Use / })[1]);
    expect(screen.getByLabelText('Email')).toHaveValue('judge-approver1@eios-demo.example.org');
    expect(screen.getByLabelText('Password')).toHaveValue('judge-demo-2026');
  });

  it('shows no card when nothing is configured', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404, json: () => Promise.resolve({}) }) as unknown as typeof fetch;
    render(<LoginPage />);
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(screen.queryByTestId('reviewer-access')).toBeNull();
  });
});
