'use client';

/**
 * Near-Final SAR Draft Narrative Composer
 * Enforces AML Investigator Workstation Rigor and Statutory Citations.
 * Embeds 100% metric citations, statutory compliance normalization (FinCEN / MFSA / LFSA),
 * and one-click submission to Governed Action Shelf.
 * Strict Institutional Light Mode.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { SarDraftDocument } from '../state/cockpit-types';
import { useStageRequest } from './use-stage-request';

interface SarComposerProps {
  draft?: SarDraftDocument;
  onSave?: (updatedText: string) => void;
}

const DEFAULT_DRAFT: SarDraftDocument = {
  caseId: 'CASE-AML-88219-LATAM',
  subjectName: 'LatAm High-Frequency Broker Cluster',
  subjectAccountId: 'ACC-88219',
  suspiciousActivityType: 'STRUCTURING_AND_MIRROR_COLLUSION',
  summaryNarrative:
    'Between 2026-09-01 and 2026-10-10, Account ACC-88219 executed 412 coordinated transactions totaling $1,420,000 USD, exhibiting 99.2% tick-level execution alignment with counterparty accounts ACC-99412 and ACC-33104 over shared hardware fingerprint DEV-F89A. Total turnover exceeded expected KYC baseline by 4.8x with a round-trip loss/profit ratio of 3.8x, strongly indicating artificial commission laundering and structuring.',
  transactionHistorySummary:
    '412 transactions across LatAm index CFD pairs; average lot size 25.0; net commission generated $142,390 USD.',
  totalTurnover: 1420000,
  netLossProfitRatio: 3.8,
  statutoryCitations: [
    '31 U.S.C. § 5318(g) (Suspicious Transaction Reporting)',
    '31 CFR § 1020.320 (Reports by Banks of Suspicious Transactions)',
    'FinCEN Form 111 (SAR Narrative Structure)',
  ],
  generatedTimestamp: '2026-10-10T09:30:00Z',
  status: 'DRAFT',
};

/**
 * The composer for the selected case. Engine-backed cases bring their own draft; the sample draft is only for the
 * fixture workstation. The body is keyed by case so switching cases never carries one case's edits to another.
 */
export function SarComposer({ draft, onSave }: SarComposerProps) {
  const { state } = useCockpit();
  const engine = state.dataOrigin === 'engine';
  const chosen = draft ?? (engine ? state.caseExtras.sarDraft : DEFAULT_DRAFT);
  if (!chosen) {
    return (
      <div className="bg-white border border-slate-200 p-4 text-xs font-mono text-slate-500" data-testid="sar-loading">
        {state.caseStatus === 'error' ? 'No SAR draft: the case could not be loaded.' : 'Preparing the SAR draft...'}
      </div>
    );
  }
  return <SarComposerBody key={chosen.caseId} draft={chosen} onSave={onSave} engine={engine} />;
}

function SarComposerBody({ draft, onSave, engine }: { draft: SarDraftDocument; onSave?: (t: string) => void; engine: boolean }) {
  const { stageAction, state } = useCockpit();
  const staging = useStageRequest();
  const fileSar = state.caseExtras.caseActions?.fileSar ?? null;
  const [narrative, setNarrative] = React.useState(draft.summaryNarrative);
  const [isSaved, setIsSaved] = React.useState(false);

  const handleStageFiling = () => {
    if (engine) {
      if (fileSar) void staging.stage(fileSar);
      return;
    }
    // Fixture workstation only: a placeholder card. It carries no signature and claims none.
    stageAction({
      intentId: `act_sar_${Date.now()}`,
      actionType: 'FILE_SAR_SUBMISSION',
      targetEntityId: draft.subjectAccountId,
      targetEntityType: 'ACCOUNT',
      severity: 'CRITICAL',
      lifecycleState: 'STAGED',
      stagedTimestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      parameters: { caseId: draft.caseId, narrative, citations: draft.statutoryCitations, turnoverUsd: draft.totalTurnover },
      estimatedImpact: `Files a SAR and locks $${draft.totalTurnover.toLocaleString()} in assets`,
      requiresFourEyes: true,
      kmsSignatureBadge: { keyId: '', algorithm: '', signatureDigest: '', verified: false },
      fourEyesRecord: {
        initiatorOfficerId: state.operator.officerId,
        initiatorTimestamp: new Date().toISOString(),
        idpClaimValidation: false,
      },
    });
  };

  const handleSaveDraft = () => {
    setIsSaved(true);
    if (onSave) onSave(narrative);
    setTimeout(() => setIsSaved(false), 2000);
  };

  return (
    <div className="bg-white border border-slate-200 p-4 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base text-amber-700">gavel</span>
            <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
              Near-Final SAR Draft Narrative Composer
            </h3>
          </div>
          <div className="text-label font-mono text-slate-500 mt-0.5">
            Case: <span className="font-bold text-slate-800">{draft.caseId}</span> | Subject: {draft.subjectAccountId}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 bg-cx-warn-bg text-cx-warn border border-cx-warn-line font-mono text-label font-bold">
            STATUS: {draft.status}
          </span>
          <span className="text-label font-mono text-cx-muted">
            Turnover: ${draft.totalTurnover.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Statutory Citations Banner */}
      <div className="p-2.5 bg-cx-sub border border-cx-line space-y-1">
        <span className="text-label font-mono font-bold uppercase text-cx-muted block">
          Statutory Normalization Citations:
        </span>
        <div className="flex flex-wrap gap-1.5">
          {draft.statutoryCitations.length === 0 && (
            <span className="text-label font-mono text-cx-muted" data-testid="sar-no-citations">
              {draft.statutoryNote ?? 'None attached.'}
            </span>
          )}
          {draft.statutoryCitations.map((cite, i) => (
            <span
              key={i}
              className="text-label font-mono bg-white text-cx-ink-soft px-1.5 py-0.2 border border-cx-line"
            >
              {cite}
            </span>
          ))}
        </div>
      </div>

      {/* Narrative Editor Area */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-semibold text-cx-ink">
          <label htmlFor="sar-narrative-textarea">Suspicious Activity Description:</label>
          <span className="text-label font-mono text-cx-muted">{narrative.length} chars</span>
        </div>
        <textarea
          id="sar-narrative-textarea"
          rows={6}
          value={narrative}
          onChange={(e) => setNarrative(e.target.value)}
          className="w-full p-3 bg-white border border-cx-line text-cx-ink text-xs font-mono focus:outline-none focus:border-cx-accent rounded-none leading-relaxed"
        />
      </div>

      {staging.message && (
        <div
          role={staging.message.tone === 'error' ? 'alert' : 'status'}
          className={`p-2 text-label font-mono border ${staging.message.tone === 'error' ? 'bg-cx-bad-bg border-cx-bad-line text-cx-bad' : 'bg-cx-ok-bg border-cx-ok-line text-cx-ok'}`}
        >
          {staging.message.text}
        </div>
      )}

      {/* Action Controls */}
      <div className="flex items-center justify-between pt-2 border-t border-cx-line-soft">
        <button
          type="button"
          onClick={handleSaveDraft}
          className="px-3 py-1.5 border border-cx-line bg-cx-sub hover:bg-cx-sub-2 text-cx-ink text-xs font-medium rounded-none transition-colors cursor-pointer"
        >
          {isSaved ? 'Draft Saved ✓' : 'Save Draft Narrative'}
        </button>

        <button
          type="button"
          onClick={handleStageFiling}
          disabled={engine && (staging.busy || !fileSar)}
          title={engine && !fileSar ? 'This case has no filing action available' : undefined}
          className="px-4 py-1.5 bg-cx-bad-solid hover:bg-cx-bad text-white font-semibold text-xs rounded-none transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-60"
        >
          <span className="material-symbols-sharp text-sm">security</span>
          Stage Official SAR Filing (Four-Eyes Required)
        </button>
      </div>
    </div>
  );
}
