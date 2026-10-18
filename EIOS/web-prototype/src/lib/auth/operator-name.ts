/**
 * How an operator is named on screen. Display only: the audit trail, approvals and API calls keep the account's
 * uid and email, which are never replaced by anything here.
 *
 * Source of truth, in order: the name set on the account (Firebase `displayName`), then the mailbox name made
 * readable ("judge-approver1@..." reads "Judge Approver 1"), then a neutral label.
 */

interface NameSource {
  readonly displayName?: string | null;
  readonly email: string | null;
}

const FALLBACK = 'Operator';

const titleCase = (word: string): string => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();

/** "approver1" is two ideas, a word and a number, so the number stands apart ("Approver 1"). */
const words = (token: string): string[] => token.match(/[A-Za-z]+|\d+/g) ?? [];

export function operatorDisplayName({ displayName, email }: NameSource): string {
  const named = displayName?.trim();
  if (named) return named;
  const local = email?.split('@')[0] ?? '';
  const readable = local
    .split(/[._-]+/)
    .flatMap(words)
    .map(titleCase)
    .join(' ');
  return readable || FALLBACK;
}

export function operatorInitials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
}

/** A role claim as words ("compliance_head" reads "compliance head"). */
export function roleLabel(role: string | null | undefined): string | null {
  return role ? role.replace(/_/g, ' ') : null;
}
