'use client';

/** One exchange in the chat thread: the question, then what the assistant answered, and the entity dividers between. */

import * as React from 'react';
import type { AssistantProposal, CopilotQueryResponse } from '../state/cockpit-types';
import { MetricProvenanceBadge } from '../common/metric-provenance';
import { SimpleMarkdown } from '../common/simple-markdown';
import { AnswerStatusBanner } from './copilot-status';
import { CopilotWorking } from './copilot-working';
import { ProposalCard, ProposalState } from './copilot-proposals';

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
  turn: ChatTurn;
  proposalStates: Record<string, ProposalState>;
  onStage: (turnId: string, proposal: AssistantProposal) => void;
  onShowInDossier: () => void;
}

export function ChatTurnView({ turn, proposalStates, onStage, onShowInDossier }: ChatTurnViewProps) {
  const response = turn.response;
  const figures = response?.citedMetrics ?? [];
  return (
    <div className="space-y-2.5">
      <div className="flex justify-end">
        <div className="px-3 py-1.5 bg-slate-900 text-white text-xs font-sans max-w-[88%] break-words">{turn.query}</div>
      </div>

      {turn.isLoading ? (
        <CopilotWorking />
      ) : turn.error ? (
        <div role="alert" className="p-2.5 bg-cx-bad-bg border border-cx-bad-line text-cx-bad flex items-start gap-2 text-xs">
          <span className="material-symbols-sharp text-base">error</span>
          <span>{turn.error}</span>
        </div>
      ) : response ? (
        <div className="space-y-2.5 bg-white p-3 border border-slate-200">
          {response.assistantStatus && <AnswerStatusBanner response={response} />}
          <SimpleMarkdown
            source={response.responseMarkdown}
            className="text-xs leading-relaxed text-slate-800 font-sans"
          />

          {figures.length > 0 && (
            <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-2">
              {figures.map((m) => (
                <div key={m.metricId} className="flex flex-col gap-0.5">
                  <span className="text-label text-slate-500 capitalize">{m.name}</span>
                  <MetricProvenanceBadge metric={m} displayMode="badge" />
                </div>
              ))}
            </div>
          )}

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
