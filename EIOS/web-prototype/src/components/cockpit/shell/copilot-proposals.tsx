'use client';

/**
 * The assistant's proposals. A proposal is a draft: nothing is signed, staged or sent until a person presses Stage,
 * which calls the real stage endpoint with the request the backend built. The assistant never approves.
 */

import * as React from 'react';
import type { AssistantProposal } from '../state/cockpit-types';
import { Chip } from '../ui/chip';

export type ProposalState =
  | { phase: 'idle' }
  | { phase: 'staging' }
  | { phase: 'staged'; intentId: string; lifecycleState: string }
  | { phase: 'error'; message: string };

interface ProposalCardProps {
  proposal: AssistantProposal;
  state: ProposalState;
  onStage: (proposal: AssistantProposal) => void;
}

const usd = (value: number) => `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;

function effectLine(p: AssistantProposal): string {
  return p.expectedEffectLow === p.expectedEffectHigh
    ? `Expected effect: ${p.expectedEffectLow}`
    : `Expected effect: ${p.expectedEffectLow} to ${p.expectedEffectHigh}`;
}

export function ProposalCard({ proposal, state, onStage }: ProposalCardProps) {
  const busy = state.phase === 'staging';
  const staged = state.phase === 'staged';
  return (
    <div className="p-3 bg-blue-50/80 border border-blue-200 space-y-2">
      <div className="flex items-center gap-2">
        <Chip tone="info">Proposed by the assistant</Chip>
        {proposal.dataOrigin === 'fixture' && <Chip tone="warn">Demo data</Chip>}
        <span className="text-xs font-bold font-mono text-slate-900">{proposal.label}</span>
      </div>
      <div className="text-xs text-slate-800">{proposal.offer}</div>
      <div className="text-label text-slate-600 font-mono space-y-0.5">
        <div>Estimated cost: {usd(proposal.estimatedCostUsd)}</div>
        <div>
          {effectLine(proposal)} · {proposal.expectedEffectBasis}
        </div>
        <div>{proposal.approvalRequirement}</div>
      </div>
      <p className="text-label text-slate-500">
        Nothing is signed or sent until you stage it, and a second operator must approve it in the approvals area.
      </p>
      {state.phase === 'error' && (
        <div role="alert" className="p-2 bg-cx-bad-bg border border-cx-bad-line text-cx-bad text-label font-mono">
          {state.message}
        </div>
      )}
      <div className="flex items-center justify-between gap-3">
        {staged ? (
          <span className="text-label font-mono text-cx-ok">
            Staged · {state.intentId} · {state.lifecycleState.replaceAll('_', ' ').toLowerCase()}. It needs a second approver in
            the action shelf.
          </span>
        ) : (
          <span />
        )}
        <button
          type="button"
          disabled={busy || staged}
          onClick={() => onStage(proposal)}
          className={`px-3 py-1.5 font-medium text-xs rounded-none transition-colors flex items-center gap-1.5 shrink-0 cursor-pointer ${
            staged ? 'bg-emerald-700 text-white cursor-default' : 'bg-blue-700 hover:bg-blue-800 text-white disabled:opacity-60'
          }`}
        >
          <span className="material-symbols-sharp text-sm" aria-hidden="true">
            {staged ? 'check_circle' : busy ? 'sync' : 'post_add'}
          </span>
          {staged ? 'Staged' : busy ? 'Staging…' : 'Stage proposal'}
        </button>
      </div>
    </div>
  );
}
