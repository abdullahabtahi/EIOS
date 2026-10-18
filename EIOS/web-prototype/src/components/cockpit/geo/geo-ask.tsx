'use client';

/**
 * The geospatial assistant beside the map. Each question carries what the map shows (view, basis, selection), so "why
 * is this suspicious?" is about the selected object. An answer's map moves name objects a tool of the same turn returned;
 * the first is applied when the answer arrives and every one stays a button, so the reader can go back and forth.
 */

import * as React from 'react';
import type { AssistantProposal, CopilotQueryResponse, ViewCommand } from '../state/cockpit-types';
import { ChatDividerView, type ChatItem, type ChatTurn, ChatTurnView } from '../shell/chat-turn';
import { describeCopilotFailure } from '../shell/copilot-chat';
import type { ProposalState } from '../shell/copilot-proposals';
import { useScrollToEnd } from '../shell/use-scroll-end';
import { Icon } from '@/components/ui/icon';
import { ChatComposer } from '../shell/chat-composer';
import { ModelPicker, useModelChoice } from '../shell/model-picker';
import { GovernedActionError, stageProposal } from '@/lib/actions/governed-actions';
import { authFetch } from '@/lib/auth/token';
import { readGeoChat, readRecentQuestions, saveGeoChat } from './geo-chat-store';
import { geoSuggestions, type MapContextPayload, moveLabel } from './geo-moves';

import { GeoEvidence } from './geo-evidence';
import { GeoVerify } from './geo-verify';
import type { GeoSelection } from './geo-types';

const STEP_LABEL: Readonly<Record<string, string>> = {
  get_geo_overview: 'geography overview',
  list_geo_leads: 'ranked leads',
  get_shared_exit: 'shared exit and its ring (BigQuery Graph)',
  get_corridor: 'corridor',
  get_geo_account: 'account geography and links (BigQuery Graph)',
  get_jurisdiction: 'jurisdiction standing and exposure',
  get_list_change_impact: 'list change and its graph links (BigQuery Graph)',
  get_aml_dossier: 'AML dossier',
  draft_sar: 'SAR draft',
  propose_hold: 'hold proposal',
  search_regulations: 'regulation search',
};

const newId = (prefix: string) => `${prefix}_${Date.now()}_${typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID().slice(0, 8) : Math.random().toString(36).slice(2, 8)}`;
const timeLabel = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

/** An icon for what the question is about, drawn from the same family as the rest of the map's controls. */
const CONTEXT_ICON: Readonly<Record<NonNullable<GeoSelection>['kind'], string>> = {
  country: 'flag',
  corridor: 'swap_horiz',
  mismatch: 'swap_horiz',
  gateway: 'router',
  account: 'person',
};

class AskError extends Error {
  constructor(
    readonly status: number,
    readonly reason?: string,
  ) {
    super(`geo assistant error (HTTP ${status})`);
  }
}

export interface GeoAskProps {
  readonly context: MapContextPayload;
  readonly selected: GeoSelection;
  /** Put the pick down, so the next question is about the whole book again. */
  readonly onClearSelection?: () => void;
  /** Apply one of an answer's map moves; `auto` is true for the move applied when the answer arrives. */
  readonly onMove: (move: ViewCommand, auto: boolean) => void;
  /** An answer is being waited for, or is not. */
  readonly onPending?: (pending: boolean) => void;
  /** Whether there is a conversation on screen, so the window can offer to start a new one. */
  readonly onThread?: (has: boolean) => void;
  /** Changes each time the reader asks for a new conversation. */
  readonly newChatSignal?: number;
  /** An answer has arrived. */
  readonly onAnswered?: () => void;
  /** A request to be ready for a question: focus the box, and put the given text in it (not sent). The id changes with each request. */
  readonly intent?: { readonly id: number; readonly text?: string } | null;
}

function selectionKey(selected: GeoSelection): string | null {
  return selected ? moveLabel(selected) : null;
}

/** Which tools the answer read, in order, and how long the turn took: the trace an investigator can check. */
function TurnTrace({ response }: { readonly response: CopilotQueryResponse }) {
  const read = response.steps.map((s) => STEP_LABEL[s] ?? s.replaceAll('_', ' '));
  if (read.length === 0) return null;
  const seconds = response.turnLatencyMs ? ` · ${(response.turnLatencyMs / 1000).toFixed(1)} s` : '';
  return (
    <p className="text-label text-cx-muted" data-testid="geo-turn-trace">
      Read: {[...new Set(read)].join(' · ')}
      {seconds}
    </p>
  );
}

function TurnMoves({ moves, onMove }: { readonly moves: readonly ViewCommand[]; readonly onMove: GeoAskProps['onMove'] }) {
  if (moves.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5" aria-label="Shown on the map">
      <span className="text-label text-cx-muted">On the map:</span>
      {moves.map((m) => (
        <button
          key={`${m.kind}:${m.id}`}
          type="button"
          onClick={() => onMove(m, false)}
          className="flex cursor-pointer items-center gap-1 border border-cx-line bg-white px-2 py-0.5 text-label text-cx-ink hover:border-cx-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cx-accent"
        >
          <Icon icon="my_location" size="sm" />
          {moveLabel(m)}
        </button>
      ))}
    </div>
  );
}

export function GeoAsk({ context, selected, onClearSelection, onMove, onPending, onAnswered, onThread, newChatSignal, intent }: GeoAskProps) {
  const [items, setItems] = React.useState<ChatItem[]>(() => [...readGeoChat().items]);
  const [proposalStates, setProposalStates] = React.useState<Record<string, ProposalState>>(() => ({ ...readGeoChat().proposalStates }));
  const [query, setQuery] = React.useState('');
  const [pending, setPending] = React.useState(false);
  const models = useModelChoice();
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  // A request to be ready for a question is answered once per id: the text lands in the box during the render that sees it.
  const [seenIntent, setSeenIntent] = React.useState<number | null>(null);
  const onScreen = selectionKey(selected);

  const listRef = useScrollToEnd<HTMLDivElement>(items);
  // Settled turns are kept for the session; a turn still loading is not (it would come back as a spinner that never ends).
  React.useEffect(() => {
    saveGeoChat({ items: items.filter((i) => i.kind !== 'turn' || !i.isLoading), proposalStates });
  }, [items, proposalStates]);

  React.useEffect(() => onPending?.(pending), [pending, onPending]);
  React.useEffect(() => onThread?.(items.length > 0), [items.length, onThread]);

  // A new conversation empties the screen only: the questions asked stay offered below, and the assistant's own record of the session is not edited.
  const [seenNewChat, setSeenNewChat] = React.useState(newChatSignal);
  if (newChatSignal !== seenNewChat) {
    setSeenNewChat(newChatSignal);
    setItems([]);
    setProposalStates({});
  }
  // A question already offered above is not listed twice.
  const offered = geoSuggestions(selected);
  const recent = items.length === 0 ? readRecentQuestions().filter((q) => !offered.includes(q)) : [];

  if (intent && seenIntent !== intent.id) {
    setSeenIntent(intent.id);
    if (intent.text !== undefined) setQuery(intent.text);
  }
  const intentId = intent?.id;
  React.useEffect(() => {
    if (intentId !== undefined) inputRef.current?.focus();
  }, [intentId]);

  const ask = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    const turn: ChatTurn = { kind: 'turn', id: newId('turn'), query: trimmed, timestamp: timeLabel(), entityId: onScreen, isLoading: true };
    setItems((current) => {
      const last = [...current].reverse().find((i): i is ChatTurn => i.kind === 'turn');
      const divider: ChatItem[] = last && last.entityId !== onScreen ? [{ kind: 'divider', id: newId('div'), entityId: onScreen }] : [];
      return [...current, ...divider, turn];
    });
    setQuery('');
    setPending(true);
    const settle = (change: Partial<ChatTurn>) =>
      setItems((current) => current.map((i) => (i.id === turn.id ? { ...(i as ChatTurn), isLoading: false, ...change } : i)));
    try {
      const res = await authFetch('/api/cockpit/copilot/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed, role: 'geospatial', mapContext: context, ...(models.selected ? { model: models.selected } : {}) }),
      });
      if (!res.ok) {
        const failure = await res.json().catch(() => null);
        const said = failure && failure.fallback_reason && typeof failure.response === 'string' ? failure.response : undefined;
        throw new AskError(res.status, said);
      }
      const data: CopilotQueryResponse = await res.json();
      settle({ response: data });
      onAnswered?.();
      const first = data.viewCommands?.[0];
      if (first) onMove(first, true);
    } catch (err) {
      settle({ error: err instanceof AskError ? describeCopilotFailure(err.status, err.reason) : describeCopilotFailure(null) });
    } finally {
      setPending(false);
    }
  };

  const stage = async (turnId: string, proposal: AssistantProposal) => {
    const key = `${turnId}:${proposal.proposalRef}`;
    setProposalStates((prev) => ({ ...prev, [key]: { phase: 'staging' } }));
    try {
      const card = await stageProposal(proposal.stageRequest);
      setProposalStates((prev) => ({ ...prev, [key]: { phase: 'staged', intentId: card.intentId, lifecycleState: card.lifecycleState } }));
    } catch (err) {
      const message = err instanceof GovernedActionError ? err.message : 'Staging failed. Nothing was staged.';
      setProposalStates((prev) => ({ ...prev, [key]: { phase: 'error', message } }));
    }
  };

  return (
    <section aria-label="Ask about the map" className="flex h-full min-h-0 flex-col bg-white">
      <div ref={listRef} className="flex-1 space-y-4 overflow-y-auto border-t border-cx-line-soft p-4 scrollbar-thin">
        {items.length === 0 ? (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold leading-snug text-cx-ink">Ask why the map shows what it shows</h3>
            <p className="text-label text-cx-muted">
              Every figure is checked against what a tool returned, and the map moves only to what a tool found.
            </p>
            <ul className="-mx-4 divide-y divide-cx-line-soft pt-1">
              {offered.map((s) => (
                <li key={s}>
                  <button
                    type="button"
                    onClick={() => ask(s)}
                    className="w-full cursor-pointer px-4 py-2 text-left text-xs text-cx-ink outline-none transition-colors hover:bg-cx-sub-2 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent">
                    {s}
                  </button>
                </li>
              ))}
            </ul>
            {recent.length > 0 && (
              <>
                <h4 className="pt-3 text-label font-semibold text-cx-muted">Asked earlier</h4>
                <ul className="-mx-4 divide-y divide-cx-line-soft">
                  {recent.map((q) => (
                    <li key={q}>
                      <button
                        type="button"
                        onClick={() => ask(q)}
                        className="w-full cursor-pointer px-4 py-2 text-left text-xs text-cx-ink-soft outline-none transition-colors hover:bg-cx-sub-2 hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent">
                        {q}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        ) : (
          items.map((item) =>
            item.kind === 'divider' ? (
              <ChatDividerView key={item.id} divider={item} />
            ) : (
              <div key={item.id} className="space-y-1.5">
                <ChatTurnView
                  variant="plain"
                  turn={{ ...item, entityId: null }}
                  proposalStates={proposalStates}
                  onStage={stage}
                  onShowInDossier={() => undefined}
                />
                {item.response && <TurnMoves moves={item.response.viewCommands ?? []} onMove={onMove} />}
                {item.response && <TurnTrace response={item.response} />}
                {item.response?.assistantStatus === 'ASSEMBLED' && (
                  <GeoVerify figures={item.response.citedMetrics} role="geospatial" />
                )}
                {item.response?.evidenceBundleId && <GeoEvidence bundleId={item.response.evidenceBundleId} />}
              </div>
            ),
          )
        )}
      </div>

      <ChatComposer
        value={query}
        onChange={setQuery}
        onSubmit={() => void ask(query)}
        placeholder={onScreen ? `Ask about the ${onScreen}…` : 'Ask about the map…'}
        ariaLabel="Ask the geospatial assistant"
        sendLabel="Ask"
        pending={pending}
        inputRef={inputRef}
        context={
          onScreen ? (
            <span
              className="inline-flex max-w-full items-center gap-1 text-label text-cx-ink-soft"
              data-testid="geo-ask-context"
              title={`Questions are about the ${onScreen} on the map`}
            >
              <Icon icon={CONTEXT_ICON[selected?.kind ?? 'country']} size="sm" className="text-cx-muted" />
              <span className="truncate font-medium">{onScreen}</span>
              {onClearSelection && (
                <button
                  type="button"
                  onClick={onClearSelection}
                  aria-label="Ask about the whole book instead"
                  title="Ask about the whole book instead"
                  className="flex size-5 shrink-0 cursor-pointer items-center justify-center text-cx-muted outline-none hover:bg-cx-sub-2 hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent">
                  <Icon icon="close" size="sm" />
                </button>
              )}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-label text-cx-muted" data-testid="geo-ask-context" title="Nothing is selected, so questions are about the whole book">
              <Icon icon="public" size="sm" />
              Whole book
            </span>
          )
        }
        accessory={<ModelPicker choices={models.choices} selected={models.selected} onSelect={models.select} />}
      />
    </section>
  );
}
