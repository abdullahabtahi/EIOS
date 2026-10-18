'use client';

import * as React from 'react';
import type { DemoAccess } from '@/lib/auth/demo-access';

interface EvaluatorAccountsProps {
  readonly access: DemoAccess;
  readonly copied: boolean;
  readonly onUse: (email: string, password: string) => void;
  readonly onCopyPassword: () => void;
}

/** Shared demo accounts an owner chose to publish. Each row names the account first; the mailbox wraps instead of cutting off. */
export function EvaluatorAccounts({ access, copied, onUse, onCopyPassword }: EvaluatorAccountsProps) {
  return (
    <section aria-labelledby="evaluator-accounts-title" className="fde-login-accounts" data-testid="reviewer-access">
      <h2 id="evaluator-accounts-title" className="fde-login-label">
        Evaluator accounts
      </h2>
      <p className="fde-login-note">
        {access.note ??
          'Shared demo accounts for evaluators. Client activity in this build is synthetic; the reference layers are real public data.'}
      </p>
      <ul className="fde-login-rows">
        {access.accounts.map((account) => (
          <li key={account.email} className="fde-login-row">
            <span className="fde-login-row-text">
              <span className="fde-login-row-name">{account.label}</span>
              <span className="fde-login-row-mono">{account.email}</span>
            </span>
            <button
              type="button"
              className="fde-login-chip"
              aria-label={`Use ${account.label}`}
              onClick={() => onUse(account.email, access.password)}
            >
              Use
            </button>
          </li>
        ))}
        <li className="fde-login-row fde-login-row-pw">
          <span className="fde-login-row-text">
            <span className="fde-login-row-name">Password, all accounts</span>
            <span className="fde-login-row-mono" data-testid="reviewer-password">
              {access.password}
            </span>
          </span>
          <button type="button" className="fde-login-chip" onClick={onCopyPassword}>
            {copied ? 'Copied' : 'Copy'}
          </button>
        </li>
      </ul>
    </section>
  );
}
