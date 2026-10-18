'use client';

import { useAuth } from '@/lib/auth/auth-context';
import { operatorDisplayName, operatorInitials, roleLabel } from '@/lib/auth/operator-name';
import { useCockpit } from '../state/cockpit-context';

export interface OperatorIdentity {
  readonly name: string;
  readonly initials: string;
  readonly role: string;
  /** The account's mailbox when signed in; shown as a tooltip so the real identity is one hover away. */
  readonly email: string | null;
}

/** One answer to "who is signed in" for every part of the shell, so the header and the rail never disagree. */
export function useOperatorIdentity(): OperatorIdentity {
  const { operator: account } = useAuth();
  const { state } = useCockpit();
  if (account) {
    const name = operatorDisplayName(account);
    return { name, initials: operatorInitials(name), role: roleLabel(account.role) ?? 'operator', email: account.email };
  }
  const name = state.operator.name;
  return {
    name,
    initials: operatorInitials(name),
    role: state.operator.clearanceLevel.replace(/_/g, ' '),
    email: null,
  };
}
