'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth/auth-context';

/** Renders children only for a signed-in operator (or when auth is disabled for local development). */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (status === 'signedOut') router.replace('/login');
  }, [status, router]);

  if (status === 'disabled' || status === 'signedIn') return <>{children}</>;
  return (
    <div role="status" className="flex min-h-screen items-center justify-center bg-cx-canvas text-cx-muted font-mono text-label uppercase tracking-wider">
      Verifying operator session…
    </div>
  );
}
