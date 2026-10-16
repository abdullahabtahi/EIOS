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
import { ModelPicker, useModelChoice } from '../shell/model-picker';
import { GovernedActionError, stageProposal } from '@/lib/actions/governed-actions';
import { authFetch } from '@/lib/auth/token';
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

const newId = (prefix: string) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
const timeLabel = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

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
  /** Apply one of an answer's map moves; `auto` is true for the move applied when the answer arrives. */
  readonly onMove: (move: ViewCommand, auto: boolean) => void;
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
          <span className="material-symbols-sharp text-sm" aria-hidden="true">
            my_location
          </span>
          {moveLabel(m)}
        </button>
      ))}
    </div>
  );
}

export function GeoAsk({ context, selected, onMove }: GeoAskProps) {
  const [items, setItems] = React.useState<ChatItem[]>([]);
  const [proposalStates, setProposalStates] = React.useState<Record<string, ProposalState>>({});
  const [query, setQuery] = React.useState('');
  const [pending, setPending] = React.useState(false);
  const models = useModelChoice();
  const endRef = React.useRef<HTMLDivElement>(null);
  const onScreen = selectionKey(selected);

  React.useEffect(() => {
    if (typeof endRef.current?.scrollIntoView === 'function') endRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [items]);

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
    <section aria-label="Ask about the map" className="flex h-full min-h-0 flex-col bg-cx-wash-0">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-cx-line bg-cx-sub px-3 py-2 text-xs">
        <span className="min-w-0 truncate text-cx-muted" data-testid="geo-ask-context">
          {onScreen ? `About the ${onScreen} on the map` : 'Nothing selected: ask about the whole book'}
        </span>
        <ModelPicker choices={models.choices} selected={models.selected} onSelect={models.select} />
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-3 scrollbar-thin">
        {items.length === 0 ? (
          <div className="space-y-3 py-6 text-center">
            <p className="text-xs font-semibold text-cx-ink">Ask why the map shows what it shows</p>
            <p className="text-label text-cx-muted">
              Every figure is checked against what a tool returned, and the map moves only to what a tool found.
            </p>
            <div className="flex flex-col items-stretch gap-2">
              {geoSuggestions(selected).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => ask(s)}
                  className="cursor-pointer border border-slate-300 bg-white px-2.5 py-1.5 text-left text-label text-slate-700 hover:border-cx-accent"
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
              <div key={item.id} className="space-y-1.5">
                <ChatTurnView
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
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(query);
        }}
        className="shrink-0 border-t border-slate-200 bg-slate-50 p-2.5"
      >
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={onScreen ? `Ask about the ${onScreen}…` : 'Ask about the map…'}
            aria-label="Ask the geospatial assistant"
            className="min-w-0 flex-1 rounded-none border border-slate-300 bg-white px-3 py-2 text-xs text-slate-900 focus:border-blue-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={pending || !query.trim()}
            className="shrink-0 cursor-pointer rounded-none bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-black disabled:opacity-40"
          >
            {pending ? 'Working…' : 'Ask'}
          </button>
        </div>
      </form>
    </section>
  );
}
