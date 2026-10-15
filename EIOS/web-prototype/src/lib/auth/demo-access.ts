/**
 * Reviewer access: shared demo accounts shown on the login page so reviewers and judges can sign in. The values come
 * from the web service's own environment at run time (`EIOS_DEMO_ACCESS`, JSON), never from the repository or the build,
 * and exist only where an owner set them. The password is deliberately public, so these accounts hold nothing but the
 * demo's synthetic data; unsetting the variable removes the card.
 */

export interface DemoAccount {
  label: string;
  email: string;
}

export interface DemoAccess {
  password: string;
  accounts: DemoAccount[];
  note?: string;
}

const MAX_ACCOUNTS = 6;
const MAX_TEXT = 200;

const text = (value: unknown): string | null =>
  typeof value === 'string' && value.trim().length > 0 && value.length <= MAX_TEXT ? value.trim() : null;

/** The configured access, or null when it is absent or malformed (the card is then simply not shown). */
export function parseDemoAccess(raw: string | undefined | null): DemoAccess | null {
  if (!raw) return null;
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!value || typeof value !== 'object') return null;
  const body = value as Record<string, unknown>;
  const password = text(body.password);
  if (!password || !Array.isArray(body.accounts) || body.accounts.length === 0 || body.accounts.length > MAX_ACCOUNTS) {
    return null;
  }
  const accounts: DemoAccount[] = [];
  for (const entry of body.accounts) {
    const item = (entry ?? {}) as Record<string, unknown>;
    const label = text(item.label);
    const email = text(item.email);
    if (!label || !email || !email.includes('@')) return null;
    accounts.push({ label, email });
  }
  const note = text(body.note);
  return { password, accounts, ...(note ? { note } : {}) };
}
