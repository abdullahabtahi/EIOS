'use client';

/**
 * What the answer says about itself. The ADK assistant does not run the Metric Auditor Gate: it fills every figure
 * in from a governed result and reports one of four statuses. A clean answer shows no banner; only a blocked,
 * failed-closed or unavailable answer does. A legacy copilot answer has no status and keeps the Metric Auditor Gate
 * reading. Nothing here calls an answer "audit passed" unless the backend's audit did.
 */

import * as React from 'react';
import type { CopilotQueryResponse } from '../state/cockpit-types';

type Tone = 'ok' | 'warn' | 'bad';

const TONE_BOX: Record<Tone, string> = {
  ok: 'bg-cx-ok-bg border-cx-ok-line text-cx-ok',
  warn: 'bg-cx-warn-bg border-cx-warn-line text-cx-warn',
  bad: 'bg-cx-bad-bg border-cx-bad-line text-cx-bad',
};

interface Banner {
  tone: Tone;
  icon: string;
  title: string;
  detail: string;
}

function bannerOf(r: CopilotQueryResponse): Banner | null {
  switch (r.assistantStatus) {
    case 'ASSEMBLED':
      return null; // a clean answer needs no banner; the figures carry their own provenance
    case 'BLOCKED':
      return {
        tone: 'bad',
        icon: 'gpp_bad',
        title: 'BLOCKED BY POLICY',
        detail:
          r.blockReason === 'output'
            ? 'The answer was withheld by output screening.'
            : 'Your question was stopped by input screening.',
      };
    case 'FAILED_CLOSED':
      return {
        tone: 'warn',
        icon: 'rule',
        title: 'COULD NOT VERIFY: NO FIGURES SHOWN',
        detail: 'The assistant could not support a complete answer from governed data. Rephrase, or ask for one specific figure.',
      };
    case 'UNAVAILABLE':
      return {
        tone: 'warn',
        icon: 'cloud_off',
        title: 'ASSISTANT UNAVAILABLE',
        detail: r.fallbackReason ? `Nothing was invented: ${r.fallbackReason}.` : 'Nothing was invented.',
      };
    default:
      return null;
  }
}

export function AnswerStatusBanner({ response }: { response: CopilotQueryResponse }) {
  const banner = bannerOf(response);
  if (!banner) return null;
  return (
    <div className={`p-2.5 border flex items-center justify-between gap-3 text-xs font-mono ${TONE_BOX[banner.tone]}`}>
      <div className="flex items-center gap-2">
        <span className="material-symbols-sharp text-base" aria-hidden="true">
          {banner.icon}
        </span>
        <div>
          <span className="font-bold tracking-tight">{banner.title}</span>
          <div className="text-label opacity-90">{banner.detail}</div>
        </div>
      </div>
    </div>
  );
}

/** The legacy copilot's Metric Auditor Gate reading. An answer with no assistant status is read this way. */
export function LegacyAuditBanner({ response }: { response: CopilotQueryResponse }) {
  const auditPassed = Boolean(response.auditorResult?.auditPassed);
  const anchoredCount = response.auditorResult?.anchoredNumbers?.length ?? 0;
  const untraceableCount = response.auditorResult?.untraceableNumbers?.length ?? 0;
  const toolTracesCount = response.auditorResult?.toolTracesCount ?? (auditPassed ? 1 : 0);
  return (
    <>
      {auditPassed ? (
        anchoredCount > 0 ? (
          <div className="p-2.5 bg-cx-ok-bg border border-cx-ok-line text-cx-ok flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base">verified</span>
              <div>
                <span className="font-bold tracking-tight">METRIC AUDITOR GATE: AUDIT PASSED</span>
                <div className="text-label opacity-90">
                  Anchored {anchoredCount} numbers against semantic tool traces.
                </div>
              </div>
            </div>
            <span className="px-2 py-0.5 bg-white/80 border border-current text-label font-bold">
              {toolTracesCount} Tool Traces Verified
            </span>
          </div>
        ) : (
          <div className="p-2.5 bg-cx-ok-bg-2 border border-cx-ok-line-2 text-cx-ok-strong flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base">verified_user</span>
              <div>
                <span className="font-bold tracking-tight">SYSTEM GUIDANCE: QUALITATIVE PROVENANCE VERIFIED</span>
                <div className="text-label opacity-90">
                  Principle I & III: Zero unanchored claims. Institutional capability explanation.
                </div>
              </div>
            </div>
            <span className="px-2 py-0.5 bg-white/80 border border-current text-label font-bold">
              Qualitative Pass
            </span>
          </div>
        )
      ) : (
        <div className="p-2.5 bg-cx-bad-bg border border-cx-bad-line text-cx-bad flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base">gpp_bad</span>
            <div>
              <span className="font-bold tracking-tight">METRIC AUDITOR GATE: BLOCKED</span>
              <div className="text-label opacity-90">
                {untraceableCount > 0
                  ? `Flagged ${untraceableCount} unanchored hallucinated numbers.`
                  : 'Unauthorized operation or speculative inquiry blocked.'}
              </div>
            </div>
          </div>
          <span className="px-2 py-0.5 bg-white/80 border border-current text-label font-bold">
            Policy Blocked
          </span>
        </div>
      )}
    </>
  );
}
