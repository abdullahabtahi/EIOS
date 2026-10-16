'use client';

/**
 * The chat view of the dossier column. One thread per workstation, kept while the operator looks at the dossier.
 * A quiet divider marks where the entity on screen changed. Figures come back as governed badges; a proposal stages
 * into the action shelf below, which stays visible.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import type { AssistantProposal, CopilotQueryResponse } from '../state/cockpit-types';
import { GovernedActionError, stageProposal } from '@/lib/actions/governed-actions';
import { authFetch } from '@/lib/auth/token';
import { ChatDividerView, ChatItem, ChatTurn, ChatTurnView } from './chat-turn';
import { suggestedQuestions } from './chat-suggestions';
import type { ProposalState } from './copilot-proposals';
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
  const inputRef = React.useRef<HTMLInputElement>(null);
  const endRef = React.useRef<HTMLDivElement>(null);
  const items = threads[role] ?? [];

  const patch = (forRole: string, change: (items: ChatItem[]) => ChatItem[]) =>
    setThreads((all) => ({ ...all, [forRole]: change(all[forRole] ?? []) }));

  React.useEffect(() => {
    if (typeof endRef.current?.scrollIntoView === 'function') endRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [items]);

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
      <div className="px-3 py-2 bg-cx-sub border-b border-cx-line shrink-0 flex items-center justify-between gap-2 text-xs">
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
        <div className="flex items-center gap-2 shrink-0">
          <ModelPicker choices={models.choices} selected={models.selected} onSelect={models.select} />
          {items.length > 0 && (
            <button
              type="button"
              onClick={() => patch(role, () => [])}
              className="text-label text-slate-500 hover:text-slate-900 underline cursor-pointer shrink-0"
              title="Clear this conversation"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-4">
        {items.length === 0 ? (
          <div className="py-8 text-center space-y-4">
            <div className="space-y-1">
              <p className="text-xs font-semibold text-slate-800">Ask about what you are looking at</p>
              <p className="text-label text-slate-500">Explain a risk, find what needs attention, or propose an action for a second operator to approve.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => ask(s)}
                  className="px-2.5 py-1 bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 text-label transition-colors cursor-pointer hover:border-blue-500"
                >
                  {s}
                </button>
              ))}
            </div>
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
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(query);
        }}
        className="border-t border-slate-200 bg-slate-50 p-2.5 shrink-0"
      >
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && inputRef.current?.blur()}
            placeholder={entityId ? `Ask about ${entityId}…` : 'Ask the copilot…'}
            aria-label="Ask the copilot"
            className="flex-1 min-w-0 px-3 py-2 bg-white border border-slate-300 text-slate-900 text-xs focus:outline-none focus:border-blue-600 rounded-none"
          />
          <button
            type="submit"
            disabled={pending > 0 || !query.trim()}
            className="px-3 py-2 bg-slate-900 hover:bg-black text-white text-xs font-medium rounded-none disabled:opacity-40 cursor-pointer shrink-0"
          >
            {pending > 0 ? 'Working…' : 'Send'}
          </button>
        </div>
      </form>
    </section>
  );
}
