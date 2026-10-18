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

const EMPTY: GeoChatThread = { items: [], proposalStates: {} };
let thread: GeoChatThread = EMPTY;

export const readGeoChat = (): GeoChatThread => thread;

export function saveGeoChat(next: GeoChatThread): void {
  thread = next;
}

export function clearGeoChat(): void {
  thread = EMPTY;
}
