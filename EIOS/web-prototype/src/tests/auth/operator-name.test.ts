import { describe, expect, it } from 'vitest';
import { operatorDisplayName, operatorInitials, roleLabel } from '@/lib/auth/operator-name';

describe('operatorDisplayName', () => {
  it('prefers the name set on the account', () => {
    expect(operatorDisplayName({ displayName: ' Amira Haddad ', email: 'a.h@bank.example' })).toBe('Amira Haddad');
  });

  it('reads the reviewer accounts as people-sized names, keeping approver 1 and 2 apart', () => {
    expect(operatorDisplayName({ email: 'judge-analyst@eios-demo.example.org' })).toBe('Judge Analyst');
    expect(operatorDisplayName({ email: 'judge-approver1@eios-demo.example.org' })).toBe('Judge Approver 1');
    expect(operatorDisplayName({ email: 'judge-approver2@eios-demo.example.org' })).toBe('Judge Approver 2');
    expect(operatorDisplayName({ email: 'analyst@eios-demo.example.org' })).toBe('Analyst');
  });

  it('title-cases a real mailbox without its domain', () => {
    expect(operatorDisplayName({ email: 'jane.doe_smith@corp.example' })).toBe('Jane Doe Smith');
  });

  it('falls back to a neutral label rather than an empty one', () => {
    expect(operatorDisplayName({ email: null })).toBe('Operator');
    expect(operatorDisplayName({ displayName: '  ', email: '@x.org' })).toBe('Operator');
  });
});

describe('operatorInitials', () => {
  it('uses the first letters of the first two words', () => {
    expect(operatorInitials('Judge Approver 1')).toBe('JA');
    expect(operatorInitials('Amira')).toBe('AM');
    expect(operatorInitials('')).toBe('?');
  });
});

describe('roleLabel', () => {
  it('reads a role claim as words', () => {
    expect(roleLabel('compliance_head')).toBe('compliance head');
    expect(roleLabel(null)).toBeNull();
  });
});
