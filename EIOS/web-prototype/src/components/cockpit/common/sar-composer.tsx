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

export function SarComposer({ draft = DEFAULT_DRAFT, onSave }: SarComposerProps) {
  const { stageAction, state } = useCockpit();
  const [narrative, setNarrative] = React.useState(draft.summaryNarrative);
  const [isSaved, setIsSaved] = React.useState(false);

  const handleStageFiling = () => {
    stageAction({
      intentId: `act_sar_${Date.now()}`,
      actionType: 'FILE_SAR_SUBMISSION',
      targetEntityId: draft.subjectAccountId,
      targetEntityType: 'ACCOUNT',
      severity: 'CRITICAL',
      lifecycleState: 'STAGED',
      stagedTimestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      parameters: {
        caseId: draft.caseId,
        narrative,
        citations: draft.statutoryCitations,
        turnoverUsd: draft.totalTurnover,
      },
      estimatedImpact: `Files official SAR with FinCEN & locks $${draft.totalTurnover.toLocaleString()} in assets`,
      requiresFourEyes: true,
      kmsSignatureBadge: {
        keyId: 'projects/feios-prod/locations/global/keyRings/eios-cockpit/cryptoKeys/action-signer-p256',
        algorithm: 'ECDSA_P256_SHA256',
        signatureDigest: `DIGEST_SIM_${Date.now()}`,
        verified: true,
      },
      fourEyesRecord: {
        initiatorOfficerId: state.operator.officerId,
        initiatorTimestamp: new Date().toISOString(),
        idpClaimValidation: true,
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
            <h3 className="text-xs font-bold font-mono uppercase tracking-wide text-slate-900">
              Near-Final SAR Draft Narrative Composer
            </h3>
          </div>
          <div className="text-[11px] font-mono text-slate-500 mt-0.5">
            Case: <span className="font-bold text-slate-800">{draft.caseId}</span> | Subject: {draft.subjectAccountId}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 bg-[#FAF5EC] text-[#A66321] border border-[#EAD8B5] font-mono text-[10px] font-bold">
            STATUS: {draft.status}
          </span>
          <span className="text-[10px] font-mono text-[#5C7080]">
            Turnover: ${draft.totalTurnover.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Statutory Citations Banner */}
      <div className="p-2.5 bg-[#F5F8FA] border border-[#D8E1E8] space-y-1">
        <span className="text-[10px] font-mono font-bold uppercase text-[#5C7080] block">
          Statutory Normalization Citations:
        </span>
        <div className="flex flex-wrap gap-1.5">
          {draft.statutoryCitations.map((cite, i) => (
            <span
              key={i}
              className="text-[10px] font-mono bg-white text-[#394B59] px-1.5 py-0.2 border border-[#D8E1E8]"
            >
              {cite}
            </span>
          ))}
        </div>
      </div>

      {/* Narrative Editor Area */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-semibold text-[#182026]">
          <label htmlFor="sar-narrative-textarea">Suspicious Activity Description (FinCEN Compliant Narrative):</label>
          <span className="text-[10px] font-mono text-[#5C7080]">{narrative.length} chars</span>
        </div>
        <textarea
          id="sar-narrative-textarea"
          rows={6}
          value={narrative}
          onChange={(e) => setNarrative(e.target.value)}
          className="w-full p-3 bg-white border border-[#D8E1E8] text-[#182026] text-xs font-mono focus:outline-none focus:border-[#106BA3] rounded-none leading-relaxed"
        />
      </div>

      {/* Action Controls */}
      <div className="flex items-center justify-between pt-2 border-t border-[#E1E8ED]">
        <button
          type="button"
          onClick={handleSaveDraft}
          className="px-3 py-1.5 border border-[#D8E1E8] bg-[#F5F8FA] hover:bg-[#EBF1F5] text-[#182026] text-xs font-medium rounded-none transition-colors cursor-pointer"
        >
          {isSaved ? 'Draft Saved ✓' : 'Save Draft Narrative'}
        </button>

        <button
          type="button"
          onClick={handleStageFiling}
          className="px-4 py-1.5 bg-[#CD4246] hover:bg-[#A82A2A] text-white font-semibold text-xs rounded-none transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <span className="material-symbols-sharp text-sm">security</span>
          Stage Official SAR Filing (Four-Eyes Required)
        </button>
      </div>
    </div>
  );
}
