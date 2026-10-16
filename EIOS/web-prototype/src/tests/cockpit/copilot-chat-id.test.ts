import { describe, it, expect } from 'vitest';
import { generateChatId } from '@/components/cockpit/shell/copilot-chat';

describe('CopilotChat ID generator', () => {
  it('generates unique IDs prefixed as requested', () => {
    const id1 = generateChatId('turn');
    const id2 = generateChatId('turn');
    expect(id1.startsWith('turn_')).toBe(true);
    expect(id2.startsWith('turn_')).toBe(true);
    expect(id1).not.toBe(id2);
  });

  it('supports different prefix types', () => {
    const threadId = generateChatId('thread');
    expect(threadId.startsWith('thread_')).toBe(true);
  });
});
