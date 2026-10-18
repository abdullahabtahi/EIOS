'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';
import { APP_HOME_HREF } from '@/components/cockpit/shell/app-nav-items';
import { EvaluatorAccounts } from '@/components/auth/login/evaluator-accounts';
import { EvaluatorGuide } from '@/components/auth/login/evaluator-guide';
import { StackSvg } from '@/components/landing/StackSvg';
import '@/components/landing/landing.css';
import '@/components/auth/login/login.css';
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
    if (status === 'signedIn' || status === 'disabled') router.replace(APP_HOME_HREF);
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
    <div className="fde fde-login">
      <header className="fde-nav fde-login-nav">
        <Link href="/" className="fde-wordmark" aria-label="EIOS home">
          EIOS
        </Link>
        <span aria-hidden="true" />
        <Link href="/" className="fde-nav-cta">
          <span aria-hidden="true">←</span> The case study
        </Link>
      </header>

      <main className="fde-login-grid">
        <div className="fde-login-art" aria-hidden="true">
          <div className="fde-stack">
            <StackSvg active={null} />
          </div>
        </div>

        <div className="fde-login-left">
          <section className="fde-login-intro" aria-labelledby="login-heading">
            <p className="fde-crumb">
              <span className="fde-crumb-pill">Operator access</span>
              <span className="fde-crumb-arrow" aria-hidden="true" />
              <span>Financial services</span>
            </p>
            <h1 id="login-heading" className="fde-login-display">
              Every action is attributed to a person.
            </h1>
            <p className="fde-lede">
              Access is limited to provisioned operators. Nothing changes state without a second approver, and every approval
              carries your identity.
            </p>
          </section>

          <EvaluatorGuide />
        </div>

        <form onSubmit={onSubmit} aria-labelledby="login-title" className="fde-login-form">
          <h2 id="login-title" className="fde-login-label">
            Operator sign-in
          </h2>
          <label className="fde-login-field" htmlFor="email">
            <span>Email</span>
            <input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="fde-login-field" htmlFor="password">
            <span>Password</span>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="fde-login-error">
              {error}
            </p>
          )}
          <button type="submit" disabled={busy} className="fde-login-submit">
            {busy ? 'Signing in…' : 'Sign in'} <span aria-hidden="true">→</span>
          </button>
        </form>

        {access && (
          <div className="fde-login-accounts-slot">
            <EvaluatorAccounts
              access={access}
              copied={copied}
              onUse={(nextEmail, nextPassword) => {
                setEmail(nextEmail);
                setPassword(nextPassword);
                setError(null);
              }}
              onCopyPassword={copyPassword}
            />
          </div>
        )}
      </main>
    </div>
  );
}
