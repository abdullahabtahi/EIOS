'use client';

/**
 * AML Investigator Workstation View (User Story 3)
 * Features priority triage queue, one-screen evidence dossier,
 * interactive relational graph with dynamic CGNAT hub suppression (k > 100),
 * near-final SAR draft narrative composer, and Active Learning Flywheel feedback loop.
 * Strict Institutional Light Mode.
 */

import * as React from 'react';
import { TopologicalGraphCanvas } from '../common/topological-graph';
import { SarComposer } from '../common/sar-composer';
import { MetricProvenanceBadge } from '../common/metric-provenance';

export function AmlWorkstationView() {
  return (
    <div className="space-y-6 text-slate-900 pb-10">
      {/* Surface 1: Relational Graph with CGNAT Hub Suppression (Anchor: panel-graph) */}
      <div
        role="tabpanel"
        id="panel-graph"
        aria-label="Relational Graph Canvas"
        className="block"
      >
        <TopologicalGraphCanvas />
      </div>

      {/* Surface 2: Near-Final SAR Draft Composer (Anchor: panel-sar) */}
      <div
        role="tabpanel"
        id="panel-sar"
        aria-label="SAR Draft Composer"
        className="block"
      >
        <SarComposer />
      </div>

      {/* Surface 3: Evidence Summary KPI Strip (Anchor: panel-dossier) */}
      <div
        role="tabpanel"
        id="panel-dossier"
        aria-label="Evidence Summary Dossier"
        className="block"
      >
        <section aria-label="AML Evidence KPI Strip" className="bg-white border border-slate-200 p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div className="flex items-center gap-2">
              <span className="material-symbols-sharp text-base text-rose-600">shield_with_heart</span>
              <h3 className="text-title font-sans font-semibold tracking-normal text-slate-900">
                One-Screen Evidence Dossier: ACC-88219 (LatAm Primary)
              </h3>
            </div>
            <span className="text-label font-mono bg-rose-100 text-rose-800 px-1.5 py-0.5 border border-rose-200 font-bold">
              SEVERITY: CRITICAL (SCORE: 0.94)
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 bg-slate-50 border border-slate-200">
              <span className="text-label text-slate-500 block">Total 30D Turnover</span>
              <div className="text-base font-bold text-slate-900 mt-0.5">$1,420,000</div>
              <span className="text-label text-rose-600 font-semibold block mt-0.5">4.8x KYC Baseline</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200">
              <span className="text-label text-slate-500 block">Round-Trip Loss/Profit</span>
              <div className="text-base font-bold text-amber-700 mt-0.5">3.8x Ratio</div>
              <span className="text-label text-slate-500 block mt-0.5">Structuring Pattern</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200">
              <span className="text-label text-slate-500 block">Tick Alignment</span>
              <div className="text-base font-bold text-rose-700 mt-0.5">99.2%</div>
              <span className="text-label text-slate-500 block mt-0.5">Mirror Trade Match</span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200">
              <span className="text-label text-slate-500 block">Hardware Fingerprint</span>
              <div className="text-sm font-bold text-slate-800 mt-0.5">DEV-F89A</div>
              <span className="text-label text-purple-700 font-semibold block mt-0.5">2 Linked Accounts</span>
            </div>
          </div>

          {/* Semantic Provenance Anchors */}
          <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
            <MetricProvenanceBadge
              metric={{
                metricId: 'M-AML-VOL-882',
                name: 'Turnover Velocity Spike',
                rawValue: 1420000,
                formattedValue: '$1.42M',
                unit: 'USD',
                semanticDefinitionVersion: 'v2.4.1 [d8a9f2]',
                asOfTimestamp: '2026-10-10T10:00:00Z',
                originEngine: 'realtime:flink',
                stewardRole: 'Lead AML Officer',
                citation: '[SPIKE]',
                isCached: false,
              }}
              displayMode="badge"
            />
            <MetricProvenanceBadge
              metric={{
                metricId: 'M-AML-MIRROR-RATIO',
                name: 'Mirror Collusion Ratio',
                rawValue: 0.992,
                formattedValue: '99.2%',
                unit: 'corr',
                semanticDefinitionVersion: 'v2.4.1 [d8a9f2]',
                asOfTimestamp: '2026-10-10T10:00:00Z',
                originEngine: 'duckdb:semantic_layer',
                stewardRole: 'Lead AML Officer',
                citation: '[TARGET]',
                isCached: false,
              }}
              displayMode="badge"
            />
          </div>
        </section>
      </div>
    </div>
  );
}
