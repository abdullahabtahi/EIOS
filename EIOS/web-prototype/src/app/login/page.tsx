'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import type { DemoAccess } from '@/lib/auth/demo-access';

export default function LoginPage() {
  const { status, signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [access, setAccess] = React.useState<DemoAccess | null>(null);
  const [copied, setCopied] = React.useState(false);

  React.useEffect(() => {
    let live = true;
    fetch('/api/demo-access', { cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : null))
      .then((body: DemoAccess | null) => {
        if (live && body && Array.isArray(body.accounts) && typeof body.password === 'string') setAccess(body);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  const copyPassword = async () => {
    if (!access) return;
    try {
      await navigator.clipboard.writeText(access.password);
      setCopied(true);
    } catch {
      setCopied(false); // the password is on screen: it can still be selected by hand
    }
  };

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
    <main className="flex min-h-screen flex-col items-center justify-center bg-cx-canvas px-4 py-8">
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
      {access && (
        <section
          aria-labelledby="reviewer-access-title"
          className="mt-4 w-full max-w-sm border border-cx-line bg-white p-6"
          data-testid="reviewer-access"
        >
          <h2 id="reviewer-access-title" className="text-xs font-bold uppercase tracking-wider text-cx-ink">
            Reviewer access
          </h2>
          <p className="mt-1 text-xs text-cx-muted">
            {access.note ?? 'Shared demo accounts for reviewers and judges. All data in this build is synthetic.'}
          </p>
          <ul className="mt-3 space-y-2">
            {access.accounts.map((account) => (
              <li key={account.email} className="flex items-center justify-between gap-2 text-xs">
                <span className="min-w-0">
                  <span className="block font-semibold text-cx-ink-soft">{account.label}</span>
                  <span className="block truncate font-mono text-cx-muted">{account.email}</span>
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword(access.password);
                    setError(null);
                  }}
                  className="shrink-0 border border-cx-line-strong px-2 py-1 font-semibold text-cx-ink hover:border-cx-accent"
                >
                  Use
                </button>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex items-center justify-between gap-2 border-t border-cx-line pt-3 text-xs">
            <span>
              <span className="block font-semibold text-cx-ink-soft">Password (all accounts)</span>
              <span className="block font-mono text-cx-ink" data-testid="reviewer-password">
                {access.password}
              </span>
            </span>
            <button
              type="button"
              onClick={copyPassword}
              className="shrink-0 border border-cx-line-strong px-2 py-1 font-semibold text-cx-ink hover:border-cx-accent"
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </section>
      )}
    </main>
  );
}
