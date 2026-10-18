'use client';

/**
 * The two ends of the dark global chrome row (brand and operator), shared by the workstation header and the
 * geospatial header so the shell reads the same on every page. The middle (telemetry, Ask) stays with the page
 * that has the state to drive it.
 */

import * as React from 'react';
import { useOperatorIdentity } from './use-operator-identity';
import { useAuth } from '@/lib/auth/auth-context';

// An environment name (STAGE, PROD) is shown only when one is configured; there is no default label.
const ENV_LABEL = process.env.NEXT_PUBLIC_EIOS_ENV;

export interface ChromeBrandProps {
  /** The page or product name shown after the brand, e.g. "OPERATOR COCKPIT v2.4". */
  readonly section: string;
  /** Render the section as the page's h1 and keep it visible at every width. */
  readonly heading?: boolean;
}

export function ChromeBrand({ section, heading = false }: ChromeBrandProps) {
  const SECTION = 'text-label text-slate-400 font-mono tracking-wider uppercase';
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-baseline gap-1.5">
        <span className="font-mono font-bold tracking-widest text-xs text-white uppercase">EIOS</span>
        {heading ? (
          <>
            <span aria-hidden="true" className={SECTION}>/</span>
            <h1 className={`${SECTION} text-slate-200`}>{section}</h1>
          </>
        ) : (
          <span className={`${SECTION} hidden sm:inline`}>/ {section}</span>
        )}
      </div>
      <span className="px-1.5 py-0.5 bg-white/8 border border-white/15 text-slate-200 font-mono text-label font-bold tracking-wider">
        {ENV_LABEL ? `${ENV_LABEL} • ` : ''}TLP:AMBER
      </span>
    </div>
  );
}

/** Who is signed in, with sign out. Falls back to the cockpit's operator when auth is off. */
export function ChromeOperator() {
  const { status: authStatus, signOutOperator } = useAuth();
  const identity = useOperatorIdentity();
  return (
    <div className="flex items-center gap-2 pl-2 border-l border-chrome-line" title={identity.email ?? undefined}>
      <div className="size-6 bg-white/10 border border-white/15 text-white flex items-center justify-center font-mono font-bold text-label">
        {identity.initials}
      </div>
      <div className="hidden xl:block text-left">
        <div data-testid="chrome-operator-name" className="text-label font-bold text-white leading-tight">
          {identity.name}
        </div>
        <div className="text-label font-mono text-slate-400 leading-tight uppercase tracking-wider">{identity.role}</div>
      </div>
      {authStatus === 'signedIn' && (
        <button
          type="button"
          onClick={() => void signOutOperator()}
          className="ml-1 px-2 py-1 border border-white/15 text-label font-mono uppercase tracking-wider text-slate-300 hover:bg-white/10 outline-none focus-visible:ring-2 focus-visible:ring-chrome-accent"
        >
          Sign out
        </button>
      )}
    </div>
  );
}
