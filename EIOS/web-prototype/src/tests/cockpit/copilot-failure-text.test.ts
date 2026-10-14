import { describe, expect, it } from 'vitest';
import { describeCopilotFailure } from '@/components/cockpit/shell/copilot-chat';

describe('Copilot failure text says what happened', () => {
  it('uses the backend\'s own words when it answered but could not produce an answer', () => {
    const timeout = 'That took longer than the time allowed, so I stopped. Please try a narrower question.';
    expect(describeCopilotFailure(503, timeout)).toBe(timeout);
  });

  it('says offline only when the backend gave no reason', () => {
    expect(describeCopilotFailure(503)).toBe('The EIOS backend is offline. No answer was generated.');
  });

  it('never lets a reason change an authorization failure', () => {
    expect(describeCopilotFailure(401, 'anything')).toContain('HTTP 401');
    expect(describeCopilotFailure(403, 'anything')).toContain('HTTP 403');
  });

  it('keeps the unreachable and generic messages', () => {
    expect(describeCopilotFailure(null)).toContain('could not be reached');
    expect(describeCopilotFailure(500)).toContain('HTTP 500');
  });
});
