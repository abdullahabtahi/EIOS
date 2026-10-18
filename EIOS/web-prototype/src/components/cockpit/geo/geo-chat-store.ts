import type { ChatItem } from '../shell/chat-turn';
import type { ProposalState } from '../shell/copilot-proposals';

/**
 * The geospatial chat, kept for the session. The workstation unmounts when the analyst switches to another one, and the
 * backend thread (per operator) carries on, so the screen takes its thread back from here instead of starting empty.
 * Held in memory only: a reload or a sign-out starts a fresh thread, as the backend session does.
 */
export interface GeoChatThread {
  readonly items: readonly ChatItem[];
  readonly proposalStates: Readonly<Record<string, ProposalState>>;
}

/** [ASSUMPTION] enough to find a question asked a little while ago without becoming a history to manage. */
export const RECENT_QUESTIONS = 5;

const EMPTY: GeoChatThread = { items: [], proposalStates: {} };
let thread: GeoChatThread = EMPTY;
let recent: readonly string[] = [];

export const readGeoChat = (): GeoChatThread => thread;

/** The last few distinct questions of this session, newest first. They outlive "New chat" so a question can be asked again. */
export const readRecentQuestions = (): readonly string[] => recent;

export function saveGeoChat(next: GeoChatThread): void {
  thread = next;
  const asked = next.items.flatMap((i) => (i.kind === 'turn' ? [i.query] : [])).reverse();
  recent = [...new Set([...asked, ...recent])].slice(0, RECENT_QUESTIONS);
}

export function clearGeoChat(): void {
  thread = EMPTY;
  recent = [];
}
