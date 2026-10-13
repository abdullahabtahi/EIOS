'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';

export default function LoginPage() {
  const { status, signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (status === 'signedIn' || status === 'disabled') router.replace('/cockpit');
  }, [status, router]);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email.trim(), password);
    } catch {
      // One message for every failure: never reveal whether an account exists.
      setError('Sign-in failed. Check your credentials and try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-cx-canvas px-4">
      <form onSubmit={onSubmit} aria-labelledby="login-title" className="w-full max-w-sm border border-cx-line bg-white p-6">
        <h1 id="login-title" className="text-sm font-bold uppercase tracking-wider text-cx-ink">
          EIOS Operator Sign-in
        </h1>
        <p className="mt-1 text-xs text-cx-muted">Access is limited to provisioned operators. Actions are attributed to your identity.</p>
        <label className="mt-5 block text-xs font-semibold text-cx-ink-soft" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mt-1 w-full border border-cx-line-strong bg-white px-3 py-2 text-sm text-cx-ink outline-none focus:border-cx-accent"
        />
        <label className="mt-4 block text-xs font-semibold text-cx-ink-soft" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mt-1 w-full border border-cx-line-strong bg-white px-3 py-2 text-sm text-cx-ink outline-none focus:border-cx-accent"
        />
        {error && (
          <p role="alert" className="mt-3 text-xs text-red-700">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="mt-5 w-full bg-cx-ink px-3 py-2 text-xs font-bold uppercase tracking-wider text-white hover:bg-cx-ink-hover disabled:opacity-60"
        >
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </main>
  );
}
