'use client';

/**
 * The chat view of the dossier column. One thread per workstation, kept while the operator looks at the dossier.
 * A quiet divider marks where the entity on screen changed. Figures come back as governed badges; a proposal stages
 * into the action shelf below, which stays visible.
 */

import * as React from 'react';
import { useScrollToEnd } from './use-scroll-end';
import { useCockpit } from '../state/cockpit-context';
import type { AssistantProposal, CopilotQueryResponse } from '../state/cockpit-types';
import { GovernedActionError, stageProposal } from '@/lib/actions/governed-actions';
import { authFetch } from '@/lib/auth/token';
import { ChatDividerView, ChatItem, ChatTurn, ChatTurnView } from './chat-turn';
import { suggestedQuestions } from './chat-suggestions';
import type { ProposalState } from './copilot-proposals';
import { ChatComposer } from './chat-composer';
import { ModelPicker, useModelChoice } from './model-picker';

/** An operator-readable reason for a failed copilot request. Never an answer. */
export function describeCopilotFailure(status: number | null, reason?: string): string {
  // The backend answered but could not produce one (a timeout, a model failure) and said so in plain words: use them,
  // never "offline", which would blame the connection for something the backend reported itself.
  if (status === 503 && reason) return reason;
  if (status === null) return 'The Copilot could not be reached. No answer was generated.';
  if (status === 401) return 'Your session is not authorized for the Copilot (HTTP 401). Sign in again.';
  if (status === 403) return 'Your role is not permitted to use the Copilot (HTTP 403).';
  if (status === 429) return 'Too many questions in a short time. Wait a moment and ask again. No answer was generated.';
  if (status === 503) return 'The EIOS backend is offline. No answer was generated.';
  return `The Copilot request failed (HTTP ${status}). No answer was generated.`;
}

class CopilotRequestError extends Error {
  constructor(
    readonly status: number,
    readonly reason?: string,
  ) {
    super(`Copilot query error (HTTP ${status})`);
  }
}

let chatCounter = 0;
export const generateChatId = (prefix: string) => {
  const cryptoObj = typeof globalThis !== 'undefined' ? globalThis.crypto : undefined;
  if (cryptoObj && typeof cryptoObj.randomUUID === 'function') {
    return `${prefix}_${Date.now()}_${cryptoObj.randomUUID().slice(0, 8)}`;
  }
  if (cryptoObj && typeof cryptoObj.getRandomValues === 'function') {
    const buf = new Uint32Array(1);
    cryptoObj.getRandomValues(buf);
    return `${prefix}_${Date.now()}_${buf[0].toString(36)}`;
  }
  chatCounter = (chatCounter + 1) % 1e6;
  return `${prefix}_${Date.now()}_${chatCounter.toString(36)}`;
};
const newId = generateChatId;
const timeLabel = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

function lastEntity(items: ChatItem[]): string | null | undefined {
  for (let i = items.length - 1; i >= 0; i -= 1) {
    const item = items[i];
    if (item.kind === 'turn') return item.entityId;
  }
  return undefined; // no turn yet
}

export function CopilotChat() {
  const { state, stageAction, showDossier, markChatUnread } = useCockpit();
  const role = state.activeRole;
  const entityId = state.activeEntityId ?? null;
  const entityItem = entityId ? state.triageItems.find((i) => i.entityId === entityId) : undefined;

  const [threads, setThreads] = React.useState<Record<string, ChatItem[]>>({});
  const [proposalStates, setProposalStates] = React.useState<Record<string, ProposalState>>({});
  const [query, setQuery] = React.useState('');
  const models = useModelChoice();
  const [pending, setPending] = React.useState(0);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  const items = threads[role] ?? [];

  const patch = (forRole: string, change: (items: ChatItem[]) => ChatItem[]) =>
    setThreads((all) => ({ ...all, [forRole]: change(all[forRole] ?? []) }));

  const listRef = useScrollToEnd<HTMLDivElement>(items);

  React.useEffect(() => {
    if (state.chatFocusTick === 0) return;
    const t = setTimeout(() => inputRef.current?.focus(), 0);
    return () => clearTimeout(t);
  }, [state.chatFocusTick]);

  const ask = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pending > 0) return;
    const turn: ChatTurn = { kind: 'turn', id: newId('turn'), query: trimmed, timestamp: timeLabel(), entityId, isLoading: true };
    const askedAs = role;
    patch(askedAs, (current) => {
      const before = lastEntity(current);
      const divider: ChatItem[] =
        before !== undefined && before !== entityId ? [{ kind: 'divider', id: newId('div'), entityId }] : [];
      return [...current, ...divider, turn];
    });
    setQuery('');
    setPending((n) => n + 1);
    const settle = (change: Partial<ChatTurn>) =>
      patch(askedAs, (current) => current.map((i) => (i.id === turn.id ? { ...(i as ChatTurn), isLoading: false, ...change } : i)));
    try {
      const res = await authFetch('/api/cockpit/copilot/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmed,
          role: askedAs,
          activeEntityId: entityId,
          ...(models.selected ? { model: models.selected } : {}),
        }),
      });
      if (!res.ok) {
        const failure = await res.json().catch(() => null);
        const said = failure && failure.fallback_reason && typeof failure.response === 'string' ? failure.response : undefined;
        throw new CopilotRequestError(res.status, said);
      }
      const data: CopilotQueryResponse = await res.json();
      settle({ response: data });
    } catch (err) {
      settle({
        error: err instanceof CopilotRequestError ? describeCopilotFailure(err.status, err.reason) : describeCopilotFailure(null),
      });
    } finally {
      setPending((n) => n - 1);
      markChatUnread();
    }
  };

  const stage = async (turnId: string, proposal: AssistantProposal) => {
    const key = `${turnId}:${proposal.proposalRef}`;
    setProposalStates((prev) => ({ ...prev, [key]: { phase: 'staging' } }));
    try {
      const card = await stageProposal(proposal.stageRequest);
      stageAction(card); // the shelf shows the card the backend made, signed and ledgered by the intent hub
      setProposalStates((prev) => ({
        ...prev,
        [key]: { phase: 'staged', intentId: card.intentId, lifecycleState: card.lifecycleState },
      }));
    } catch (err) {
      const message = err instanceof GovernedActionError ? err.message : 'Staging failed. Nothing was staged.';
      setProposalStates((prev) => ({ ...prev, [key]: { phase: 'error', message } }));
    }
  };

  const suggestions = suggestedQuestions(role, entityId ? { id: entityId, kind: entityItem?.entityType ?? '' } : null);

  return (
    <section aria-label="Copilot chat" className="w-full min-w-0 h-full flex flex-col bg-cx-wash-0">
      <div className="px-3 py-2 bg-cx-sub border-b border-cx-line shrink-0 text-xs">
        <div className="min-w-0" data-testid="chat-context">
          {entityId ? (
            <>
              <span className="font-mono font-bold text-cx-ink">{entityId}</span>
              {entityItem && <span className="text-cx-muted"> · {entityItem.title}</span>}
              {entityItem?.subtitle && <div className="text-label text-cx-muted truncate">{entityItem.subtitle}</div>}
            </>
          ) : (
            <span className="text-cx-muted">No entity selected. Pick one from the triage rail, or ask in general.</span>
          )}
        </div>
      </div>

      <div ref={listRef} className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-4">
        {items.length === 0 ? (
          <div className="space-y-2 pt-2">
            <h3 className="text-sm font-semibold leading-snug text-cx-ink">Ask about what you are looking at</h3>
            <p className="text-label text-cx-muted">Explain a risk, find what needs attention, or propose an action for a second operator to approve.</p>
            <ul className="-mx-3 divide-y divide-cx-line-soft pt-1">
              {suggestions.map((s) => (
                <li key={s}>
                  <button
                    type="button"
                    onClick={() => ask(s)}
                    className="w-full cursor-pointer px-3 py-2 text-left text-xs text-cx-ink outline-none transition-colors hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent"
                  >
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          items.map((item) =>
            item.kind === 'divider' ? (
              <ChatDividerView key={item.id} divider={item} />
            ) : (
              <ChatTurnView
                key={item.id}
                turn={item}
                proposalStates={proposalStates}
                onStage={stage}
                onShowInDossier={showDossier}
              />
            ),
          )
        )}
      </div>

      <ChatComposer
        value={query}
        onChange={setQuery}
        onSubmit={() => void ask(query)}
        placeholder={entityId ? `Ask about ${entityId}…` : 'Ask the copilot…'}
        ariaLabel="Ask the copilot"
        sendLabel="Send"
        pending={pending > 0}
        inputRef={inputRef}
        onKeyDown={(e) => e.key === 'Escape' && inputRef.current?.blur()}
        context={
          items.length > 0 ? (
            <button
              type="button"
              onClick={() => patch(role, () => [])}
              title="Clear this conversation"
              className="cursor-pointer text-label text-cx-muted outline-none hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent"
            >
              Clear conversation
            </button>
          ) : undefined
        }
        accessory={<ModelPicker choices={models.choices} selected={models.selected} onSelect={models.select} />}
      />
    </section>
  );
}
