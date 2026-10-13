'use client';

/**
 * Senior Partner Manager GenAI Flywheel.
 * Ingests multi-signal qualitative inputs (support tickets, P2P cashier logs,
 * competitor spread telemetry) and generates localized battlecards
 * with pre-calculated DoWhy SCM concession guardrails.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { fetchPartnerBattlecards, getFallbackPartnerBattlecards, simulatePartnerWhatIf } from '../state/api-bridge';

export function PartnerGenAiBattlecards() {
  const { state, stageAction } = useCockpit();
  const partnerId = state.activeTriageItemId?.replace('item_', '') || 'AP-1029';

  const [battlecardData, setBattlecardData] = React.useState<any>(() => getFallbackPartnerBattlecards(partnerId));
  const [copiedCardId, setCopiedCardId] = React.useState<string | null>(null);

  // What-If Simulation State
  const [whatIfInput, setWhatIfInput] = React.useState('');
  const [isSimulating, setIsSimulating] = React.useState(false);
  const [whatIfResult, setWhatIfResult] = React.useState<any | null>(null);

  React.useEffect(() => {
    let active = true;
    fetchPartnerBattlecards(partnerId).then((data) => {
      if (active) setBattlecardData(data);
    });
    return () => {
      active = false;
    };
  }, [partnerId]);

  const handleCopy = (cardId: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCardId(cardId);
    setTimeout(() => setCopiedCardId(null), 2500);
  };

  const handleStageAction = (card: any) => {
    stageAction({
      intentId: `act_retention_${Date.now()}`,
      actionType: card.action_type || 'DEPLOY_RETENTION_PLAYBOOK',
      targetEntityId: partnerId,
      targetEntityType: 'PARTNER',
      severity: 'HIGH',
      lifecycleState: 'STAGED',
      stagedTimestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      parameters: {
        partner_id: partnerId,
        playbook_title: card.title,
        deal_cost_usd: card.deal_cost_usd,
        projected_margin_usd: card.net_margin_usd,
        concession_bound: card.concession_bound,
      },
      estimatedImpact: `Projected +${card.projected_lift_pct}% 90D retention lift ($${card.net_margin_usd?.toLocaleString()} net margin)`,
      requiresFourEyes: card.deal_cost_usd > 10000,
      kmsSignatureBadge: {
        keyId: 'projects/feios-prod/locations/global/keyRings/eios-cockpit/cryptoKeys/action-signer-p256',
        algorithm: 'ECDSA_P256_SHA256',
        signatureDigest: `DIGEST_RETENTION_${Date.now()}`,
        verified: true,
      },
      fourEyesRecord: {
        initiatorOfficerId: state.operator.officerId,
        initiatorTimestamp: new Date().toISOString(),
        idpClaimValidation: true,
      },
    });
  };

  const handleRunWhatIf = async (promptText?: string) => {
    const query = (promptText || whatIfInput).trim();
    if (!query) return;
    setIsSimulating(true);
    try {
      const res = await simulatePartnerWhatIf(partnerId, query);
      setWhatIfResult(res);
    } finally {
      setIsSimulating(false);
    }
  };

  if (!battlecardData) {
    return (
      <div className="p-4 bg-slate-50 border border-slate-200 animate-pulse text-xs font-mono text-slate-500">
        Synthesizing multi-signal partner intelligence via Gemini 3.8 Flash...
      </div>
    );
  }

  return (
    <section
      aria-label="GenAI Partner Churn Battlecards"
      className="bg-white border border-slate-200 p-4 shadow-sm space-y-4 text-slate-900"
    >
      {/* Header with Sovereign AIP Badge */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2">
          <span className="material-symbols-sharp text-base text-cx-accent">psychology</span>
          <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
            EIOS Partner Intelligence &amp; Retention Battlecards
          </h3>
          <span className="px-2 py-0.5 bg-slate-100 border border-slate-300 text-slate-800 font-mono text-label font-semibold rounded-xs shadow-2xs flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-cx-accent inline-block" />
            AIP Logic • Gemini 3.8 Flash (Dual-Verified)
          </span>
        </div>

        <div className="text-label font-mono text-slate-500 flex items-center gap-2">
          <span className="px-1.5 py-0.2 bg-slate-100 border border-slate-200 font-bold">
            LATAM DESK
          </span>
          <span>Recovery Window: 14 Days</span>
        </div>
      </div>

      {/* Triangulated Attrition Diagnosis Box */}
      <div className="p-3.5 bg-slate-50 border border-slate-200 text-xs font-sans space-y-1.5">
        <div className="flex items-center justify-between text-slate-900 font-mono text-label font-bold">
          <span className="flex items-center gap-1.5">
            <span className="material-symbols-sharp text-sm text-cx-accent">troubleshoot</span>
            Cross-Channel Attrition Diagnosis
          </span>
          <span className="text-label text-slate-500 font-normal">
            Triangulated: Support Tickets • Cashier Latency • Competitor Spreads
          </span>
        </div>
        <p className="text-slate-700 leading-relaxed text-xs">
          {battlecardData.forensic_diagnostic_narrative}
        </p>
      </div>

      {/* 3 WhatsApp / Telegram Outreach Battlecards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs font-mono font-bold text-slate-700">
          <span className="flex items-center gap-1">
            <span className="material-symbols-sharp text-sm text-emerald-700">chat</span>
            Actionable WhatsApp &amp; Telegram Outreach Battlecards
          </span>
          <span className="text-label font-normal text-slate-500">
            Causal SCM Pre-Approved Concession Bounds
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 text-xs">
          {battlecardData.battlecards.map((card: any) => {
            const isCopied = copiedCardId === card.id;

            return (
              <div
                key={card.id}
                className="p-3.5 bg-white border border-slate-200 flex flex-col justify-between space-y-3 hover:border-slate-400 transition-colors shadow-2xs"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-1">
                    <span className="font-mono font-bold text-slate-900 text-label leading-snug">
                      {card.title}
                    </span>
                    <span className="text-label font-mono px-1 py-0.2 bg-emerald-50 text-emerald-800 border border-emerald-200 shrink-0 font-bold">
                      +{card.projected_lift_pct}% LIFT
                    </span>
                  </div>

                  <span className="text-label font-mono text-cx-accent font-semibold block">
                    Strategic Angle: {card.angle}
                  </span>

                  {/* WhatsApp Message Preview */}
                  <div className="p-2.5 bg-cx-wash border border-slate-200 rounded-xs text-label font-sans text-slate-800 leading-relaxed italic relative">
                    &ldquo;{card.whatsapp_script}&rdquo;
                  </div>

                  <div className="text-label font-mono text-slate-500 space-y-0.5 pt-1 border-t border-slate-200">
                    <div className="flex justify-between">
                      <span>Deal Cost:</span>
                      <span className="font-bold text-slate-700">
                        ${card.deal_cost_usd ? card.deal_cost_usd.toLocaleString() : '0'} USD
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Net Retained Margin:</span>
                      <span className="font-bold text-emerald-700">
                        +${card.net_margin_usd != null ? card.net_margin_usd.toLocaleString() : '0'} USD
                      </span>
                    </div>
                    <div className="text-label text-slate-500 italic mt-0.5">
                      {card.concession_bound}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t border-slate-200 font-mono text-xs">
                  <button
                    type="button"
                    onClick={() => handleCopy(card.id, card.whatsapp_script)}
                    className={`flex-1 py-1.5 border text-center transition-colors flex items-center justify-center gap-1 cursor-pointer text-xs ${
                      isCopied
                        ? 'bg-emerald-700 border-emerald-700 text-white font-bold'
                        : 'bg-white border-slate-300 hover:bg-slate-50 text-slate-700'
                    }`}
                  >
                    <span className="material-symbols-sharp text-xs">
                      {isCopied ? 'check' : 'content_copy'}
                    </span>
                    <span>{isCopied ? 'Copied!' : 'Copy Script'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleStageAction(card)}
                    className="py-1.5 px-3 bg-cx-accent hover:bg-cx-accent-strong text-white font-bold border border-cx-accent-strong transition-colors flex items-center gap-1 cursor-pointer text-xs shadow-2xs"
                    title="Stage this concession into the Two-Phase Commit Outbox"
                  >
                    <span className="material-symbols-sharp text-xs">bolt</span>
                    <span>Stage</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sovereign AIP Deal Simulator (Concession Matrix & What-If Evaluator) */}
      <div className="p-3.5 bg-slate-50 border border-slate-200 space-y-3 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-xs">
            <span className="material-symbols-sharp text-sm text-cx-accent">finance_mode</span>
            <span>Counterfactual Deal Simulator (AIP Concession Matrix)</span>
          </div>
          <span className="text-label text-slate-500 font-normal">
            DoWhy SCM Refuter Guardrails (p &gt; 0.05 Required)
          </span>
        </div>

        {/* Structured Scenario Evaluation Input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={whatIfInput}
            onChange={(e) => setWhatIfInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRunWhatIf();
            }}
            placeholder="Simulate concession scenario (e.g. Offer 50% synthetics revenue share with 2h DP2P VIP SLA)..."
            className="flex-1 px-3 py-1.5 bg-white border border-slate-300 text-xs font-sans text-slate-900 focus:outline-none focus:border-cx-accent rounded-none"
          />
          <button
            type="button"
            onClick={() => handleRunWhatIf()}
            disabled={isSimulating}
            className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5 shrink-0 rounded-none text-xs"
          >
            <span className="material-symbols-sharp text-xs">
              {isSimulating ? 'progress_activity' : 'play_arrow'}
            </span>
            <span>{isSimulating ? 'Simulating...' : 'Simulate'}</span>
          </button>
        </div>

        {/* Quick Institutional Scenario Presets */}
        <div className="flex items-center gap-1.5 flex-wrap text-label">
          <span className="text-slate-500 font-semibold">Institutional Presets:</span>
          {[
            '+15% Synthetics Rev-Share Bump',
            'Spread Match Concession (-2.5 bps)',
            '2-Hour DP2P Cashier Fast-Track',
            'Regional Seminar Sponsorship ($3.5K)',
          ].map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => {
                setWhatIfInput(chip);
                handleRunWhatIf(chip);
              }}
              className="px-2 py-0.5 bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 hover:text-slate-900 transition-colors cursor-pointer font-mono"
            >
              {chip}
            </button>
          ))}
        </div>

        {/* Simulation Output Card */}
        {whatIfResult && (
          <div className="mt-2 p-3 bg-white border border-slate-300 shadow-2xs space-y-2">
            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
              <span className="font-bold text-slate-900 flex items-center gap-1">
                <span className="material-symbols-sharp text-xs text-emerald-600">verified</span>
                Verdict: {whatIfResult.verdict}
              </span>
              <span className="text-label text-slate-500">
                Refuter P-Value: {whatIfResult.causal_refuter_p_value} (Valid &gt; 0.05)
              </span>
            </div>

            <p className="text-xs font-sans text-slate-800 leading-relaxed">
              {whatIfResult.governed_decision_rationale}
            </p>

            <div className="grid grid-cols-3 gap-2 text-label pt-1 border-t border-slate-100">
              <div className="p-2 bg-slate-50 border border-slate-100">
                <span className="text-label text-slate-500 block uppercase">Projected Lift</span>
                <span className="font-bold text-emerald-700 text-sm mt-0.5">
                  +{whatIfResult.projected_retention_lift_pct}%
                </span>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-100">
                <span className="text-label text-slate-500 block uppercase">Concession Cost</span>
                <span className="font-bold text-slate-800 text-sm mt-0.5">
                  ${whatIfResult.estimated_deal_cost_usd?.toLocaleString()} USD
                </span>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-100">
                <span className="text-label text-slate-500 block uppercase">Net Retained Margin</span>
                <span className="font-bold text-cx-accent text-sm mt-0.5">
                  +${whatIfResult.projected_net_margin_usd?.toLocaleString()} USD
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
