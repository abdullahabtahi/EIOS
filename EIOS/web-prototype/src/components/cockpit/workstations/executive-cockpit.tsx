'use client';

/**
 * Executive Decision Cockpit Workstation View (User Story 2)
 * Features 4-horizon Morning Briefing feed, Strategic Countermeasure Trade-offs,
 * interactive 4-domain Causal DAG, and sub-200ms What-If Parametric Shock Slider
 * with verified 100% additive attribution waterfall.
 * Strict Institutional Light Mode.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { CausalDagCanvas } from '../common/causal-dag-canvas';
import { WhatIfSlider } from '../common/what-if-slider';
import { MetricProvenanceBadge } from '../common/metric-provenance';

const MORNING_HORIZONS = [
  {
    id: 'COMPETITIVE',
    title: 'Competitive Market Horizon',
    summary: 'LatAm spread widened 18 bps following primary broker tiering adjustment.',
    metric: {
      metricId: 'M-SPREAD-01',
      name: 'Spread Shock LatAm',
      rawValue: 18.2,
      formattedValue: '+18.2 bps',
      unit: 'bps',
      semanticDefinitionVersion: 'v2.4.1 [d8a9f2]',
      asOfTimestamp: '2026-10-10T10:00:00Z',
      originEngine: 'duckdb:semantic_layer',
      stewardRole: 'VP Market Strategy',
      citation: '[BRIEF]' as const,
      isCached: false,
    },
  },
  {
    id: 'PARTNER',
    title: 'Partner Flow Horizon',
    summary: 'Tier 1 master affiliate #882 shows mirror trading anomaly and hazard elevation.',
    metric: {
      metricId: 'M-FLOW-882',
      name: 'Partner 882 Flow Run-Rate',
      rawValue: 4200000,
      formattedValue: '$4.20M',
      unit: 'USD/mo',
      semanticDefinitionVersion: 'v2.1.0 [e4c19a]',
      asOfTimestamp: '2026-10-10T10:00:00Z',
      originEngine: 'bigquery:metrics_job',
      stewardRole: 'Head of Partnerships',
      citation: '[TARGET]' as const,
      isCached: false,
    },
  },
  {
    id: 'CLIENT',
    title: 'Client Retention Horizon',
    summary: 'VIP Tier-1 account retention sensitivity modeled with DoWhy refuter check.',
    metric: {
      metricId: 'M-CHURN-VIP',
      name: 'VIP Churn Hazard Rate',
      rawValue: 0.048,
      formattedValue: '4.8%',
      unit: 'p-hazard',
      semanticDefinitionVersion: 'v3.0.0 [b11c4e]',
      asOfTimestamp: '2026-10-10T10:00:00Z',
      originEngine: 'realtime:flink',
      stewardRole: 'Chief Commercial Officer',
      citation: '[ASSUMPTION]' as const,
      isCached: false,
    },
  },
  {
    id: 'FINANCIAL',
    title: 'Financial Metrics Horizon',
    summary: 'Quarterly run-rate projection maintains $84.5M net margin under baseline spread.',
    metric: {
      metricId: 'M-NET-MARGIN',
      name: 'Net Brokerage Operating Margin',
      rawValue: 84500000,
      formattedValue: '$84.5M',
      unit: 'USD',
      semanticDefinitionVersion: 'v2.4.1 [d8a9f2]',
      asOfTimestamp: '2026-10-10T10:00:00Z',
      originEngine: 'duckdb:semantic_layer',
      stewardRole: 'Chief Financial Officer',
      citation: '[BRIEF]' as const,
      isCached: false,
    },
  },
];

export function ExecutiveCockpitView() {
  const { stageAction, state } = useCockpit();

  return (
    <div className="space-y-6 text-slate-900 pb-10">
      {/* Surface 1: Causal DAG Canvas (Anchor: panel-dag) */}
      <div
        role="tabpanel"
        id="panel-dag"
        aria-label="Causal DAG Canvas"
        className="block"
      >
        <CausalDagCanvas />
      </div>

      {/* Surface 2: What-If Slider & Attribution Waterfall (Anchor: panel-whatif) */}
      <div
        role="tabpanel"
        id="panel-whatif"
        aria-label="What-If Parametric Waterfall"
        className="block"
      >
        <WhatIfSlider />
      </div>

      {/* Surface 3: 4-Horizon Morning Briefing Cards (Anchor: panel-briefing) */}
      <div
        role="tabpanel"
        id="panel-briefing"
        aria-label="Executive Morning Briefing"
        className="block"
      >
        <section aria-label="Morning Briefing 4 Horizons" className="space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base text-blue-600">wb_twilight</span>
              <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
                Executive Morning Briefing: 4 Causal Horizons
              </h3>
            </div>
            <span className="text-label font-mono text-slate-500">
              Synthesized across 15 Subsystems (F001–F015)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {MORNING_HORIZONS.map((h) => (
              <div
                key={h.id}
                className="p-3.5 bg-white border border-slate-200 shadow-xs flex flex-col justify-between rounded-none space-y-2"
              >
                <div>
                  <div className="flex items-center justify-between text-label font-mono mb-1">
                    <span className="font-bold text-blue-700 bg-blue-50 px-1 py-0.2 border border-blue-100">
                      {h.id === 'COMPETITIVE' ? 'COMPETITIVE' : h.id === 'PARTNER' ? 'PARTNER FLOW' : h.id === 'CLIENT' ? 'CLIENT RETENTION' : 'FINANCIAL METRICS'}
                    </span>
                    <span className="text-slate-400">08:00 UTC</span>
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 tracking-tight leading-snug">
                    {h.title}
                  </h4>
                  <p className="text-label text-slate-600 font-sans mt-1 leading-relaxed">
                    {h.summary}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <MetricProvenanceBadge metric={h.metric} displayMode="compact" />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Surface 4: Strategic Countermeasure Trade-offs (Anchor: panel-tradeoffs) */}
      <div
        role="tabpanel"
        id="panel-tradeoffs"
        aria-label="Strategic Trade-offs"
        className="block"
      >
        <section aria-label="Strategic Trade-off Analysis" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base text-slate-800">balance</span>
              <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
                Strategic Trade-off Analysis & Countermeasures
              </h3>
            </div>
            <span className="text-label font-mono bg-slate-100 text-slate-700 px-1.5 py-0.5 border border-slate-200">
              DoWhy Refuter Calibrated
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              {
                action: 'Deploy LatAm VIP Rebate Program',
                target: 'COMP-LATAM-01',
                ret: '+$4.2M retention flow',
                risk: '-$850K gross fee income',
                conf: '94%',
                sens: 'High downside if broker 2 widens > 25 bps',
              },
              {
                action: 'Re-index Dynamic Risk Spreads',
                target: 'FEED-BROKER-LATAM',
                ret: '+$1.8M hedging margin',
                risk: '+2.1% partner churn probability',
                conf: '89%',
                sens: 'Low downside under current volatility',
              },
            ].map((item, idx) => (
              <div key={idx} className="p-3 bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold font-mono text-slate-900">{item.action}</span>
                  <span className="text-label font-mono text-green-800 font-bold bg-green-50 px-1 border border-green-200">
                    Confidence: {item.conf}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-label font-mono">
                  <div className="text-green-700 font-semibold">{item.ret}</div>
                  <div className="text-amber-800 font-semibold">{item.risk}</div>
                </div>
                <div className="text-label text-slate-500 font-sans">Sensitivity: {item.sens}</div>
                <button
                  type="button"
                  onClick={() => {
                    stageAction({
                      intentId: `act_exec_${idx}_${Date.now()}`,
                      actionType: item.action,
                      targetEntityId: item.target,
                      targetEntityType: 'STRATEGIC_COUNTERMEASURE',
                      severity: 'HIGH',
                      lifecycleState: 'STAGED',
                      stagedTimestamp: new Date().toISOString(),
                      expiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
                      parameters: { countermeasure: item.action },
                      estimatedImpact: `${item.ret} return against ${item.risk}`,
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
                  }}
                  className="w-full py-1.5 bg-slate-900 hover:bg-black text-white text-xs font-semibold rounded-none cursor-pointer flex items-center justify-center gap-1 transition-colors"
                >
                  <span className="material-symbols-sharp text-xs">playlist_add</span>
                  Stage Countermeasure (Two-Phase Commit)
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
