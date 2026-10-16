'use client';

/** One exchange in the chat thread: the question, then what the assistant answered, and the entity dividers between. */

import * as React from 'react';
import type { AssistantProposal, CopilotQueryResponse, MetricProvenance } from '../state/cockpit-types';
import { MetricProvenanceBadge } from '../common/metric-provenance';
import { SimpleMarkdown } from '../common/simple-markdown';
import { AnswerStatusBanner } from './copilot-status';
import { CopilotWorking } from './copilot-working';
import { ProposalCard, ProposalState } from './copilot-proposals';
import { SourceChips } from './source-chips';

export interface ChatTurn {
  kind: 'turn';
  id: string;
  query: string;
  timestamp: string;
  entityId: string | null;
  response?: CopilotQueryResponse;
  isLoading?: boolean;
  error?: string;
}

export interface ChatDivider {
  kind: 'divider';
  id: string;
  entityId: string | null;
}

export type ChatItem = ChatTurn | ChatDivider;

const INLINE_FIGURES = 4;

/** The sentences already carry the figures; the badges are the proof. A long list folds them away until asked. */
function FigureBadges({ figures }: { figures: MetricProvenance[] }) {
  const badges = (
    <div className="flex flex-wrap gap-2">
      {figures.map((m) => (
        <div key={m.metricId} className="flex flex-col gap-0.5">
          <span className="text-label text-slate-500 capitalize">{m.name}</span>
          <MetricProvenanceBadge metric={m} displayMode="badge" />
        </div>
      ))}
    </div>
  );
  if (figures.length <= INLINE_FIGURES) return <div className="pt-2 border-t border-slate-100">{badges}</div>;
  return (
    <details className="pt-2 border-t border-slate-100">
      <summary className="text-label text-slate-500 cursor-pointer select-none">Sources for {figures.length} figures</summary>
      <div className="pt-2">{badges}</div>
    </details>
  );
}

export function ChatDividerView({ divider }: { divider: ChatDivider }) {
  return (
    <div className="flex items-center gap-2 text-label font-mono text-slate-400" role="separator">
      <span className="h-px flex-1 bg-slate-200" />
      <span>{divider.entityId ? `Now viewing ${divider.entityId}` : 'No entity on screen'}</span>
      <span className="h-px flex-1 bg-slate-200" />
    </div>
  );
}

interface ChatTurnViewProps {
  /** `plain` sets the exchange on the page's own white, with no card around the answer, for panels that already have a frame. */
  variant?: 'default' | 'plain';
  turn: ChatTurn;
  proposalStates: Record<string, ProposalState>;
  onStage: (turnId: string, proposal: AssistantProposal) => void;
  onShowInDossier: () => void;
}

export function ChatTurnView({ variant = 'default', turn, proposalStates, onStage, onShowInDossier }: ChatTurnViewProps) {
  const plain = variant === 'plain';
  const response = turn.response;
  const figures = response?.citedMetrics ?? [];
  return (
    <div className="space-y-2.5">
      <div className="flex justify-end">
        <div className={`px-3 py-1.5 text-xs font-sans max-w-[88%] break-words ${plain ? 'bg-cx-select text-cx-ink' : 'bg-slate-900 text-white'}`}>{turn.query}</div>
      </div>

      {turn.isLoading ? (
        <CopilotWorking plain={plain} />
      ) : turn.error ? (
        <div role="alert" className="p-2.5 bg-cx-bad-bg border border-cx-bad-line text-cx-bad flex items-start gap-2 text-xs">
          <span className="material-symbols-sharp text-base">error</span>
          <span>{turn.error}</span>
        </div>
      ) : response ? (
        <div className={plain ? 'space-y-2.5' : 'space-y-2.5 bg-white p-3 border border-slate-200'}>
          {response.assistantStatus && <AnswerStatusBanner response={response} />}
          <SimpleMarkdown
            source={response.responseMarkdown}
            className={`text-xs leading-relaxed font-sans ${plain ? "text-cx-ink" : "text-slate-800"}`}
          />

          {figures.length > 0 && <FigureBadges figures={figures} />}
          <SourceChips sources={response.sources ?? []} />

          {(response.proposals ?? []).map((proposal) => (
            <ProposalCard
              key={proposal.proposalRef}
              proposal={proposal}
              state={proposalStates[`${turn.id}:${proposal.proposalRef}`] ?? { phase: 'idle' }}
              onStage={(p) => onStage(turn.id, p)}
            />
          ))}

          {turn.entityId && response.assistantStatus === 'ASSEMBLED' && (
            <button
              type="button"
              onClick={onShowInDossier}
              className="text-label text-cx-accent hover:underline cursor-pointer flex items-center gap-1"
            >
              <span className="material-symbols-sharp text-sm" aria-hidden="true">
                article
              </span>
              Show in dossier
            </button>
          )}
        </div>
      ) : null}
    </div>
  );
}
