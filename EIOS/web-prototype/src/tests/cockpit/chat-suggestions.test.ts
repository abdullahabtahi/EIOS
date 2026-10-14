import { describe, expect, it } from 'vitest';
import { suggestedQuestions } from '@/components/cockpit/shell/chat-suggestions';

describe('suggestedQuestions', () => {
  it('names the entity on screen for a partner manager', () => {
    const q = suggestedQuestions('partner_manager', { id: 'PTR-723', kind: 'PARTNER' });
    expect(q.some((s) => s.includes('PTR-723'))).toBe(true);
    expect(q.length).toBeLessThanOrEqual(4);
    expect(q.join(' ')).not.toMatch(/retention offer/i); // not every partner has a deal to offer
  });

  it('asks about the worklist when nothing is selected', () => {
    const q = suggestedQuestions('partner_manager', null);
    expect(q.join(' ')).toMatch(/attention|ecosystem/i);
    expect(q.every((s) => !/PTR-|undefined|null/.test(s))).toBe(true);
  });

  it('never suggests a question about an account to a partner manager, or the reverse', () => {
    expect(suggestedQuestions('partner_manager', { id: 'CR84920', kind: 'ACCOUNT' }).join(' ')).not.toContain('CR84920');
    expect(suggestedQuestions('aml_investigator', { id: 'PTR-723', kind: 'PARTNER' }).join(' ')).not.toContain('PTR-723');
  });

  it('gives every workstation something to ask, always ending with what the assistant can do', () => {
    for (const role of ['executive', 'aml_investigator', 'partner_manager', 'compliance_auditor', 'data_operations'] as const) {
      const q = suggestedQuestions(role, null);
      expect(q.length).toBeGreaterThanOrEqual(2);
      expect(q[q.length - 1]).toBe('What can you do?');
    }
  });
});
