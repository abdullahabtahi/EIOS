/* eslint-disable @typescript-eslint/no-explicit-any */
import * as React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const replace = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ replace, push: vi.fn() }) }));

const authState = vi.hoisted(() => ({ auth: null as any, user: null as any }));
vi.mock('@/lib/auth/firebase', () => ({ getFirebaseAuth: () => authState.auth }));

import { getFirebaseConfig } from '@/lib/auth/config';
import { authFetch } from '@/lib/auth/token';
import { RequireAuth } from '@/components/auth/require-auth';
import LoginPage from '@/app/login/page';
import { AuthProvider } from '@/lib/auth/auth-context';

vi.mock('firebase/auth', () => ({
  onAuthStateChanged: vi.fn((_auth: unknown, cb: (u: unknown) => void) => {
    queueMicrotask(() => cb(authState.user ?? null));
    return () => {};
  }),
  getIdTokenResult: vi.fn(async () => ({ claims: { role: 'approver' } })),
  signInWithEmailAndPassword: vi.fn(async () => {
    throw new Error('auth/invalid-credential');
  }),
  signOut: vi.fn(),
}));
describe('firebase config', () => {
  it('is absent (auth disabled) without an api key and project', () => {
    expect(getFirebaseConfig({})).toBeNull();
    expect(getFirebaseConfig({ NEXT_PUBLIC_FIREBASE_API_KEY: 'k' })).toBeNull();
  });

  it('derives the auth domain from the project', () => {
    expect(getFirebaseConfig({ NEXT_PUBLIC_FIREBASE_API_KEY: 'k', NEXT_PUBLIC_FIREBASE_PROJECT_ID: 'p' })).toEqual({
      apiKey: 'k',
      projectId: 'p',
      authDomain: 'p.firebaseapp.com',
    });
  });
});

describe('authFetch', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset().mockResolvedValue(new Response('{}'));
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    authState.auth = null;
  });

  it('attaches the operator ID token when signed in', async () => {
    authState.auth = { currentUser: { getIdToken: async () => 'tok-123' } };
    await authFetch('/api/x');
    expect((fetchMock.mock.calls[0][1].headers as Headers).get('Authorization')).toBe('Bearer tok-123');
  });

  it('sends no Authorization header when signed out or auth is off', async () => {
    await authFetch('/api/x');
    expect((fetchMock.mock.calls[0][1].headers as Headers).has('Authorization')).toBe(false);
    authState.auth = { currentUser: null };
    await authFetch('/api/x');
    expect((fetchMock.mock.calls[1][1].headers as Headers).has('Authorization')).toBe(false);
  });

  it('preserves caller headers', async () => {
    authState.auth = { currentUser: { getIdToken: async () => 't' } };
    await authFetch('/api/x', { headers: { 'Content-Type': 'application/json' } });
    expect((fetchMock.mock.calls[0][1].headers as Headers).get('Content-Type')).toBe('application/json');
  });
});

describe('RequireAuth', () => {
  afterEach(() => {
    replace.mockReset();
    authState.auth = null;
    authState.user = null;
  });

  it('renders the cockpit when auth is disabled (local development)', () => {
    render(
      <AuthProvider>
        <RequireAuth>
          <div>cockpit</div>
        </RequireAuth>
      </AuthProvider>,
    );
    expect(screen.getByText('cockpit')).toBeInTheDocument();
  });

  it('sends a signed-out operator to the login page and hides the cockpit', async () => {
    authState.auth = {};
    render(
      <AuthProvider>
        <RequireAuth>
          <div>cockpit</div>
        </RequireAuth>
      </AuthProvider>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
    expect(screen.queryByText('cockpit')).not.toBeInTheDocument();
  });

  it('shows the cockpit to a signed-in operator', async () => {
    authState.auth = {};
    authState.user = { uid: 'u1', email: 'a@example.org' };
    render(
      <AuthProvider>
        <RequireAuth>
          <div>cockpit</div>
        </RequireAuth>
      </AuthProvider>,
    );
    expect(await screen.findByText('cockpit')).toBeInTheDocument();
  });
});

describe('LoginPage', () => {
  it('shows one generic error for any failed sign-in', async () => {
    authState.auth = {};
    authState.user = null;
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>,
    );
    fireEvent.change(await screen.findByLabelText('Email'), { target: { value: 'who@example.org' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong-password' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Sign-in failed');
    expect(alert.textContent).not.toMatch(/invalid-credential|user-not-found|wrong-password/i);
  });
});
