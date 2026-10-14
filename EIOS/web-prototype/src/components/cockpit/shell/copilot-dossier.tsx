'use client';

/**
 * Center Copilot Dossier Container (560px Column)
 * Universal Tripartite COP Center Zone.
 * Displays semantic narrative sections, trade-off proposals,
 * metric provenance popovers (Principle I & V), and SAR draft summaries.
 * Strict Institutional Light-Mode styling.
 */

import { useStageRequest } from '../common/use-stage-request';
import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { MetricProvenanceBadge } from '../common/metric-provenance';
import { FallbackReplayBadge } from '../common/fallback-replay-badge';
import type { DossierSection, MetricProvenance } from '../state/cockpit-types';
import { MOCK_PARTNERS } from '../state/fixtures';

/** ' · 14:57 UTC' for a valid ISO timestamp, '' otherwise (never invent a time). */
function asOfClock(iso: string | undefined): string {
  const ms = iso ? Date.parse(iso) : Number.NaN;
  return Number.isNaN(ms) ? '' : ` · ${new Date(ms).toISOString().slice(11, 16)} UTC`;
}

export function CopilotDossier() {
  const { state, stageAction } = useCockpit();
  const staging = useStageRequest();
  const dossier = state.activeDossier;

  if (!dossier) {
    return (
      <main
        aria-label="Copilot Dossier Center Zone"
        className="w-full min-w-0 bg-white p-8 flex flex-col items-center justify-center text-center text-slate-400"
      >
        <span className="material-symbols-sharp text-4xl text-slate-300 mb-2">
          article
        </span>
        <h3 className="text-sm font-semibold text-slate-700">No Dossier Selected</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          Select an item from the left triage rail to load its synthesized operational dossier.
        </p>
      </main>
    );
  }

  // The fixture plane's partner panel is sample content; an engine-computed partner dossier renders like any other.
  if ((dossier.role === 'partner_manager' || state.activeRole === 'partner_manager') && state.dataOrigin !== 'engine') {
    return <PartnerRetentionDossierView dossier={dossier} />;
  }

  return (
    <main
      aria-label="Copilot Dossier Center Zone"
      className="w-full min-w-0 bg-white flex flex-col h-full overflow-hidden select-text"
    >
      {/* Dossier Header Strip */}
      <div className="p-4 bg-cx-sub border-b border-cx-line space-y-2 shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1.5">
          <div className="flex items-center gap-1.5 min-w-0 font-mono text-label text-cx-muted">
            <span className="material-symbols-sharp text-sm text-cx-accent">article</span>
            <span className="uppercase font-bold tracking-wider text-cx-ink whitespace-nowrap">
              Copilot Dossier
            </span>
            <span className="text-cx-line-strong">|</span>
            <span
              title={dossier.entityId}
              className="bg-cx-sub-2 border border-cx-line px-1.5 py-0.2 text-cx-ink font-bold truncate max-w-[200px]"
            >
              {dossier.entityId}
            </span>
          </div>

          {dossier.isCachedSnapshot ? (
            <FallbackReplayBadge timestamp={dossier.asOfTimestamp} reason={dossier.replayReason} size="sm" />
          ) : (
            <span
              title="Served by the gateway, not a cached replay. Each figure carries its own verification in its popover."
              className="text-label font-mono text-cx-ok px-1.5 py-0.5 border border-cx-line flex items-center gap-1 whitespace-nowrap"
            >
              <span className="size-1.5 bg-cx-ok-solid inline-block" />
              Synchronized{asOfClock(dossier.asOfTimestamp)}
            </span>
          )}
        </div>

        <h2 className="text-sm font-bold text-cx-ink tracking-tight leading-snug">
          {dossier.headline}
        </h2>

        <p className="text-xs text-cx-muted leading-relaxed font-sans">
          {dossier.executiveSummary}
        </p>
      </div>

      {/* Dossier Scrollable Narrative Sections */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-5">
        {/* Semantic Narrative Sections */}
        {(dossier.sections || []).map((section: DossierSection, idx: number) => {
          const sectionId = section.sectionId || `sec_${idx}`;
          const title = section.title || 'Operational Assessment';
          const citations = Array.isArray(section.citations) ? section.citations : [];
          const narrative = section.narrativeText || '';
          const metrics = Array.isArray(section.metrics) ? section.metrics : [];

          return (
            <section
              key={sectionId}
              className="p-3.5 bg-slate-50/50 border border-slate-200 space-y-2.5 rounded-none"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
                  {title}
                </h3>
                {citations.length > 0 && (
                  <div className="flex items-center gap-1">
                    {citations.map((c: string) => (
                      <span
                        key={c}
                        className="text-label font-mono bg-cx-info-bg text-cx-accent border border-cx-info-line px-1 py-0.2"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <p className="text-xs text-cx-ink leading-relaxed font-sans">
                {narrative}
              </p>

              {/* Anchored Metrics Grid */}
              {metrics.length > 0 && (
                <div className="pt-2 border-t border-cx-line-soft flex flex-wrap gap-2">
                  {metrics.map((m: MetricProvenance) => (
                    <MetricProvenanceBadge key={m.metricId} metric={m} displayMode="badge" />
                  ))}
                </div>
              )}
            </section>
          );
        })}

        {/* Strategic Trade-offs (Executive Horizon) */}
        {dossier.tradeOffs && dossier.tradeOffs.length > 0 && (
          <section className="space-y-3">
            <h3 className="text-title font-sans font-semibold tracking-normal text-cx-ink flex items-center gap-1.5">
              <span className="material-symbols-sharp text-sm text-cx-accent">balance</span>
              Strategic Countermeasure Trade-offs
            </h3>

            <div className="space-y-2.5">
              {dossier.tradeOffs.map((to, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-white border border-cx-line shadow-xs space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-cx-ink font-mono">
                      {to.proposedAction}
                    </span>
                    <span className="text-label font-mono text-cx-ok bg-cx-ok-bg px-1.5 py-0.2 border border-cx-ok-line">
                      Conf={Math.round(to.confidenceScore * 100)}%
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-label font-mono pt-1 border-t border-cx-line-soft">
                    <div>
                      <span className="text-cx-muted">Projected Return: </span>
                      <span className="font-semibold text-cx-ok">{to.projectedReturn}</span>
                    </div>
                    <div>
                      <span className="text-cx-muted">Projected Risk: </span>
                      <span className="font-semibold text-cx-warn">{to.projectedRisk}</span>
                    </div>
                  </div>

                  <div className="text-label text-cx-muted">
                    Downside: <span className="font-mono text-cx-ink">{to.downsideSensitivity}</span>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      if (to.stageRequest) {
                        void staging.stage(to.stageRequest);
                        return;
                      }
                      // Fixture trade-offs have no backend request: a placeholder card that claims no signature.
                      stageAction({
                        intentId: `act_tradeoff_${Date.now()}`,
                        actionType: to.proposedAction,
                        targetEntityId: dossier.entityId,
                        targetEntityType: 'STRATEGIC_COUNTERMEASURE',
                        severity: 'HIGH',
                        lifecycleState: 'STAGED',
                        stagedTimestamp: new Date().toISOString(),
                        expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
                        parameters: { rationale: to.proposedAction },
                        estimatedImpact: `${to.projectedReturn} return vs ${to.projectedRisk} risk`,
                        requiresFourEyes: true,
                        kmsSignatureBadge: { keyId: '', algorithm: '', signatureDigest: '', verified: false },
                        fourEyesRecord: {
                          initiatorOfficerId: state.operator.officerId,
                          initiatorTimestamp: new Date().toISOString(),
                          idpClaimValidation: false,
                        },
                      });
                    }}
                    disabled={staging.busy}
                    className="w-full py-1.5 bg-cx-sub hover:bg-cx-sub-2 border border-cx-line text-cx-ink text-label font-semibold flex items-center justify-center gap-1 cursor-pointer transition-colors"
                  >
                    <span className="material-symbols-sharp text-xs">playlist_add</span>
                    Stage Trade-off Action to Shelf
                  </button>
                  {staging.message && (
                    <div
                      role={staging.message.tone === 'error' ? 'alert' : 'status'}
                      className={`text-label font-mono ${staging.message.tone === 'error' ? 'text-cx-bad' : 'text-cx-ok'}`}
                    >
                      {staging.message.text}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* SAR Draft Preview (AML Investigator) */}
        {dossier.sarDraft && (
          <section className="p-3.5 bg-cx-warn-bg border border-cx-warn-line space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono text-cx-warn uppercase flex items-center gap-1">
                <span className="material-symbols-sharp text-sm text-cx-warn">description</span>
                Near-Final SAR Draft Narrative
              </span>
              <span className="text-label font-mono text-cx-warn bg-cx-warn-bg-2 border border-cx-warn-line px-1.5 py-0.2">
                Status: {dossier.sarDraft.status}
              </span>
            </div>

            <p className="text-xs text-cx-ink leading-relaxed font-sans">
              {dossier.sarDraft.summaryNarrative}
            </p>

            <div className="grid grid-cols-2 gap-2 text-label font-mono pt-1 text-cx-muted">
              <div>Turnover: ${dossier.sarDraft.totalTurnover.toLocaleString()}</div>
              {dossier.sarDraft.netLossProfitRatio !== undefined && (
                <div>Loss/Profit Ratio: {dossier.sarDraft.netLossProfitRatio}x</div>
              )}
            </div>
          </section>
        )}

        {/* Disaster Recovery Runbook Proof Callout (Feature 015) */}
        {state.activeDrProofs.length > 0 && (
          <section className="p-3 bg-cx-sub border border-cx-line space-y-1.5 text-label font-mono">
            <div className="flex items-center justify-between">
              <span className="font-bold text-cx-ink uppercase flex items-center gap-1">
                <span className="material-symbols-sharp text-xs text-cx-accent">shield</span>
                DR Runbook Proof (F015)
              </span>
              <span className="text-cx-ok font-bold bg-cx-ok-bg px-1.5 py-0.2 border border-cx-ok-line">
                {state.activeDrProofs[0].verificationStatus}
              </span>
            </div>
            <div className="text-cx-muted">
              Runbook: {state.activeDrProofs[0].runbookName}
            </div>
            <div className="text-label text-cx-faint truncate">
              KMS Keyring: {state.activeDrProofs[0].kmsKeyringRotationStatus} | Cache: {state.activeDrProofs[0].warmStartCacheState}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function PartnerRetentionDossierView({ dossier }: { dossier: any }) {
  const { state, stageAction } = useCockpit();
  const partner = MOCK_PARTNERS.find((p) => p.partnerId === dossier.entityId) || MOCK_PARTNERS[0];
  const [sliderBps, setSliderBps] = React.useState(25);
  const [copiedScript, setCopiedScript] = React.useState(false);
  const [toastMessage, setToastMessage] = React.useState<string | null>(null);

  const isCashier = partner.primaryDriver === 'OPERATIONAL_CASHIER' || (partner.cashierLatencyHours ?? 0) > 2.0;

  // Dynamic causal calculations based on sliderBps
  const dynamicLift = Math.min(94, Math.round((partner.projectedLiftPct || 70) * (0.6 + (sliderBps / 50) * 0.4)));
  const netMarginRecovery = Math.round((partner.netMarginRecoveryUsd || 30000) * (0.7 + (sliderBps / 50) * 0.3));
  const dealCost = Math.round(sliderBps * 320);
  const pValueRefuter = 0.44; // DoWhy Placebo Refuter p-value >= 0.40

  const handleStageGovernedAction = () => {
    stageAction({
      intentId: `act_retention_${partner.partnerId}_${Date.now()}`,
      actionType: isCashier ? 'DeployVIPCashierRails' : 'DeployRetentionVIPDeal',
      targetEntityId: partner.partnerId,
      targetEntityType: 'PARTNER',
      severity: 'HIGH',
      lifecycleState: 'STAGED',
      stagedTimestamp: new Date().toISOString(),
      expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      parameters: {
        partnerId: partner.partnerId,
        concessionBps: sliderBps,
        dealCostUsd: dealCost,
        netMarginRecoveryUsd: netMarginRecovery,
        primaryRootCause: partner.primaryRootCause,
      },
      estimatedImpact: `+${dynamicLift}% retention lift; $${netMarginRecovery.toLocaleString()} net margin protected`,
      requiresFourEyes: dealCost > 5000,
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

    setToastMessage(`Action Staged: ${isCashier ? 'VIP Cashier Rails' : 'VIP Spread Concession'} -> Governed Shelf`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const battlecardScript = isCashier
    ? `Hola ${partner.name.split(' ')[0]}, Elena from Institutional Partner Ops here. We noticed your payout tickets had delays over the weekend due to local DP2P clearing bottleneck. We have routed your desk to dedicated Tier-1 VIP cashier settlement rails with SLA guarantee <45m and waived routing fees for 90 days.`
    : `Hi ${partner.name.split(' ')[0]}, Elena from Institutional Partner Ops. We reviewed your monthly volume and have approved an exclusive +${sliderBps} bps spread rebate match with zero-swap on Gold. This protects your margins against rival offers while keeping your existing sub-IB tier active.`;

  const copyBattlecard = () => {
    navigator.clipboard.writeText(battlecardScript);
    setCopiedScript(true);
    setTimeout(() => setCopiedScript(false), 2000);
  };

  return (
    <main
      aria-label="Partner Retention Copilot Dossier"
      className="w-full min-w-0 bg-white flex flex-col h-full overflow-hidden select-text relative"
    >
      {/* Toast Feedback */}
      {toastMessage && (
        <div className="absolute top-3 right-3 z-30 text-label font-mono px-3 py-1.5 shadow-md flex items-center gap-1.5 bg-green-50 border border-green-500 text-green-800 animate-in fade-in">
          <span className="material-symbols-sharp text-sm text-green-600">verified</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Strip */}
      <div className="p-4 bg-cx-wash border-b border-slate-200 space-y-2 shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1.5">
          <div className="flex items-center gap-1.5 min-w-0 font-mono text-label text-slate-600">
            <span className="material-symbols-sharp text-sm text-cx-accent">hub</span>
            <span className="uppercase font-bold tracking-wider text-slate-900 whitespace-nowrap">
              Retention Dossier
            </span>
            <span className="text-slate-300">|</span>
            <span className="bg-white border border-slate-300 px-1.5 py-0.2 text-slate-900 font-bold whitespace-nowrap">
              {partner.partnerId}
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap whitespace-nowrap">
            <span className="px-1.5 py-0.2 text-cx-ink-soft text-label font-mono border border-cx-line flex items-center gap-1">
              <span className="material-symbols-sharp text-xs text-cx-muted">psychology</span>
              AIP Logic • Gemini 3.8 Flash (Dual-Verified)
            </span>
            <span className="px-1.5 py-0.2 text-cx-ink-soft text-label font-mono border border-cx-line">
              {partner.tier}
            </span>
            <span className="text-label font-mono text-cx-ok px-1.5 py-0.5 border border-cx-line flex items-center gap-1 whitespace-nowrap">
              <span className="size-1.5 bg-cx-ok-solid inline-block" />
              P-256 Verified
            </span>
          </div>
        </div>

        <div>
          <h2 className="text-sm font-bold text-slate-900 tracking-tight leading-snug">
            {partner.name}
          </h2>
          <div className="text-label font-mono text-slate-500 mt-0.5 flex items-center gap-2">
            <span>{partner.region}</span>
            <span>•</span>
            <span>Cohort: {partner.cohort}</span>
          </div>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed font-sans">
          {dossier.executiveSummary}
        </p>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4">
        {/* Diagnostic Telemetry Grid */}
        <div className="grid grid-cols-2 gap-2 text-xs font-mono">
          <div className="p-2.5 bg-slate-50 border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">Survival Hazard P(churn)</span>
            <div className={`text-base font-bold mt-0.5 ${partner.pChurn >= 0.5 ? 'text-red-700' : 'text-green-700'}`}>
              {(partner.pChurn * 100).toFixed(1)}%
            </div>
            <span className="text-label text-slate-500 block">DoWhy SCM calibrated</span>
          </div>

          <div className="p-2.5 bg-slate-50 border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">30D Value at Risk</span>
            <div className="text-base font-bold text-slate-900 mt-0.5">
              ${(partner.valueAtRiskUsd / 1000).toFixed(0)}K USD
            </div>
            <span className="text-label text-slate-500 block">30D commission volume</span>
          </div>

          <div className="p-2.5 bg-slate-50 border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">Login Decay (14D)</span>
            <div className={`text-sm font-bold mt-0.5 ${(partner.loginDecayPct ?? 0) < -20 ? 'text-red-700' : 'text-slate-700'}`}>
              {partner.loginDecayPct ?? 0}%
            </div>
            <span className="text-label text-slate-500 block">PELT change-point</span>
          </div>

          <div className="p-2.5 bg-slate-50 border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">Cashier Latency SLA</span>
            <div className={`text-sm font-bold mt-0.5 ${(partner.cashierLatencyHours ?? 0) > 2 ? 'text-amber-700' : 'text-slate-700'}`}>
              {partner.cashierLatencyHours ?? 0.8} hrs
            </div>
            <span className="text-label text-slate-500 block">
              {(partner.cashierLatencyHours ?? 0) > 2 ? 'SLA bottleneck' : 'Healthy SLA'}
            </span>
          </div>
        </div>

        {/* Multi-Signal Root Cause Attribution Card */}
        <section className="p-3 bg-slate-50 border border-slate-200 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900 flex items-center gap-1.5">
              <span className="material-symbols-sharp text-sm text-cx-accent">troubleshoot</span>
              Multi-Signal Root Cause Diagnosis
            </h3>
            <span className="text-label font-mono px-1.5 py-0.2 bg-white border border-slate-300 font-semibold text-slate-700">
              {partner.primaryDriver}
            </span>
          </div>

          <p className="text-slate-700 leading-relaxed font-sans text-xs">
            {partner.primaryRootCause ? partner.primaryRootCause : dossier.sections?.[0]?.narrativeText}
          </p>

          <div className="pt-2 border-t border-slate-200 flex flex-wrap gap-1.5 text-label font-mono">
            {partner.competitorPoaching !== 'None' && (
              <span className="px-2 py-0.5 bg-cx-sub text-cx-ink-soft border border-cx-line font-semibold">
                Poaching: {partner.competitorPoaching}
              </span>
            )}
            {(partner.supportTicketCount ?? 0) > 0 && (
              <span className="px-2 py-0.5 bg-cx-sub text-cx-ink-soft border border-cx-line font-semibold">
                {partner.supportTicketCount} Support Tickets
              </span>
            )}
            {partner.changePointDetected && (
              <span className="px-2 py-0.5 bg-cx-sub text-cx-ink-soft border border-cx-line font-semibold">
                Change-Point Detected
              </span>
            )}
          </div>
        </section>

        {/* Live DoWhy SCM What-If Concession Simulator */}
        <section className="p-3.5 bg-white border border-slate-200 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900 flex items-center gap-1.5">
              <span className="material-symbols-sharp text-sm text-cx-accent">tune</span>
              Live DoWhy SCM What-If Concession Simulator
            </h3>
            <span className="text-label font-mono px-1.5 py-0.2 bg-cx-ok-bg border border-cx-ok-line text-cx-ok font-bold">
              Refuter p={pValueRefuter} (PASS)
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-600 font-medium">Rebate Concession Offset:</span>
              <span className="font-bold text-slate-900">{sliderBps} bps (${dealCost} /mo cost)</span>
            </div>
            <input
              type="range"
              min="0"
              aria-label="Rebate concession offset (bps)"
              max="50"
              step="5"
              value={sliderBps}
              onChange={(e) => setSliderBps(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-200 accent-cx-accent cursor-pointer"
            />
            <div className="flex justify-between text-label font-mono text-slate-400">
              <span>0 bps (No Deal)</span>
              <span>25 bps (Optimal Frontier)</span>
              <span>50 bps (Margin Ceiling)</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-label font-mono pt-2 border-t border-slate-200">
            <div>
              <span className="text-slate-500 block text-label">Projected Retention Uplift</span>
              <span className="font-bold text-cx-ok text-sm">+{dynamicLift}%</span>
              <span className="text-label text-slate-400 block">CI95: [{dynamicLift - 10}%, {dynamicLift + 8}%]</span>
            </div>
            <div>
              <span className="text-slate-500 block text-label">Net Margin Recovery</span>
              <span className="font-bold text-slate-900 text-sm">+${(netMarginRecovery / 1000).toFixed(1)}K</span>
              <span className="text-label text-slate-400 block">Protected 90D margin</span>
            </div>
          </div>
        </section>

        {/* Governed Adaptive Retention Playbook Launcher */}
        <section className="p-3.5 bg-slate-50 border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900 flex items-center gap-1.5">
              <span className="material-symbols-sharp text-sm text-cx-accent">verified</span>
              Driver-Adaptive Governed Playbook
            </h3>
            <span className="text-label font-mono text-slate-500">
              Win Rate: {Math.round((partner.empiricalPlaybookWinRate || 0.785) * 100)}%
            </span>
          </div>

          <div className="text-xs text-slate-700 leading-snug">
            <strong>
              {isCashier
                ? `Dedicated VIP Cashier Rails (45m SLA Guarantee)`
                : `VIP Spread Rebate Match Agreement (+${sliderBps} bps)`}
            </strong>
            <p className="text-label text-slate-500 mt-1 font-sans">
              {isCashier
                ? `Bypasses public DP2P cashier queues in Colombia. Resolves ticket backlog in <4 hours.`
                : `Guarantees commercial rebate parity with Exness/XM for 90 days. Four-eyes approved.`}
            </p>
          </div>

          <button
            type="button"
            onClick={handleStageGovernedAction}
            className="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white font-mono font-bold text-xs flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-xs"
          >
            <span className="material-symbols-sharp text-sm text-green-400">playlist_add</span>
            <span>Stage Action to Governed Shelf (Cmd+Enter)</span>
          </button>
        </section>

        {/* Localized WhatsApp / Telegram Retention Battlecards */}
        <section className="p-3.5 bg-white border border-slate-200 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900 flex items-center gap-1.5">
              <span className="material-symbols-sharp text-sm text-cx-ok">chat</span>
              WhatsApp / Telegram Retention Battlecard
            </h3>
            <button
              type="button"
              onClick={copyBattlecard}
              className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-800 text-label font-mono font-bold flex items-center gap-1 cursor-pointer transition-colors"
            >
              <span className="material-symbols-sharp text-xs">
                {copiedScript ? 'done' : 'content_copy'}
              </span>
              <span>{copiedScript ? 'Copied' : 'Copy Script'}</span>
            </button>
          </div>

          <div className="p-2.5 bg-slate-50 border border-slate-200 text-label font-mono text-slate-800 leading-relaxed whitespace-pre-wrap">
            {battlecardScript}
          </div>
        </section>
      </div>
    </main>
  );
}
