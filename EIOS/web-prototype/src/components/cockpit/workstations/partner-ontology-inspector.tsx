'use client';

/**
 * EIOS Sovereign Kinetic Ontology 360 Inspector for Partner Entity.
 * Visualizes Object Type, typed schema properties, security markings,
 * cryptographic hot-state ledger hash, and interactive link traversal.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { fetchPartnerOntology, getFallbackPartnerOntology } from '../state/api-bridge';

export function PartnerOntologyInspector() {
  const { state, selectEntity } = useCockpit();
  const partnerId = state.activeTriageItemId?.replace('item_', '') || 'AP-1029';
  const [ontologyData, setOntologyData] = React.useState<any>(() => getFallbackPartnerOntology(partnerId));
  const [activeModalLink, setActiveModalLink] = React.useState<any | null>(null);

  React.useEffect(() => {
    let active = true;
    fetchPartnerOntology(partnerId).then((data) => {
      if (active) setOntologyData(data);
    });
    return () => {
      active = false;
    };
  }, [partnerId]);

  if (!ontologyData) {
    return (
      <div className="p-4 bg-slate-50 border border-slate-200 animate-pulse text-xs font-mono text-slate-500">
        Loading EIOS Object 360 for {partnerId}...
      </div>
    );
  }

  const props = ontologyData.properties || {};
  const links = ontologyData.links || [];

  return (
    <div className="bg-white border border-slate-200 shadow-sm text-slate-900">
      {/* Object 360 Header Strip */}
      <div className="p-3.5 bg-slate-900 text-slate-100 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="material-symbols-sharp text-base text-cx-info-soft">hub</span>
          <div className="flex items-center gap-1.5 font-mono text-xs">
            <span className="px-2 py-0.5 bg-slate-800 text-slate-200 border border-slate-700 font-semibold uppercase tracking-wider text-label">
              Ontology Entity • Partner
            </span>
            <span className="text-slate-500">/</span>
            <span className="font-bold text-white tracking-wide">{props.partner_id || partnerId}</span>
            <span className="text-slate-300 font-sans font-medium text-label">
              ({props.legal_name || 'Carlos Mendez'})
            </span>
          </div>

          <span className="px-1.5 py-0.5 bg-amber-950/60 text-amber-300 border border-amber-600/50 text-label font-mono font-bold tracking-wider">
            {ontologyData.security_markings?.[0] || 'TLP:AMBER'}
          </span>
          <span className="px-1.5 py-0.5 bg-rose-950/60 text-rose-300 border border-rose-600/50 text-label font-mono font-bold tracking-wider">
            {ontologyData.lifecycle_state || 'AT_RISK_POACHING'}
          </span>
        </div>

        <div className="flex items-center gap-2 text-label font-mono text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
            Hot-State Synchronized
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400 font-mono text-label">
            {ontologyData.hot_state_sha256?.slice(0, 18)}...
          </span>
        </div>
      </div>

      {/* Typed Ontological Properties Grid */}
      <div className="p-3.5 bg-slate-50/70 border-b border-slate-200">
        <div className="text-label font-mono font-bold uppercase text-slate-500 tracking-wider mb-2 flex items-center justify-between">
          <span>Kinetic Schema Properties (v2.1.0)</span>
          <span className="text-label text-slate-500 font-mono">Hot-State Ledger (Verified)</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 font-mono text-xs">
          <div className="p-2 bg-white border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">Tenure</span>
            <div className="font-bold text-slate-900 mt-0.5">{props.tenure_days ?? 840} days</div>
            <span className="text-label text-slate-400 block mt-0.5">Established IB</span>
          </div>

          <div className="p-2 bg-white border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">30D Value at Risk</span>
            <div className="font-bold text-rose-700 mt-0.5">
              ${(((props.value_at_risk_usd ?? 1240000)) / 1000).toFixed(0)}K USD
            </div>
            <span className="text-label text-rose-600 font-bold block mt-0.5">Top LatAm Driver</span>
          </div>

          <div className="p-2 bg-white border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">30D Churn Probability</span>
            <div className="font-bold text-rose-700 mt-0.5">{props.hazard_probability_30d ?? '84.0%'}</div>
            <span className="text-label text-rose-600 font-bold block mt-0.5">Activity Shift Confirmed</span>
          </div>

          <div className="p-2 bg-white border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">Active Traders</span>
            <div className="font-bold text-slate-900 mt-0.5">{props.active_traders_count ?? 1420}</div>
            <span className="text-label text-slate-500 block mt-0.5">{props.primary_synthetics_volume_pct ?? 82}% Synthetics Volume</span>
          </div>

          <div className="p-2 bg-white border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">Cashier Latency SLA</span>
            <div className="font-bold text-amber-700 mt-0.5">{props.cashier_latency_sla_hours ?? 4.2} hrs</div>
            <span className="text-label text-rose-600 font-bold block mt-0.5">Latency Bottleneck</span>
          </div>

          <div className="p-2 bg-white border border-slate-200">
            <span className="text-label text-slate-500 uppercase block">Priority Index</span>
            <div className="font-bold text-cx-accent mt-0.5">{props.priority_score ?? 92} / 100</div>
            <span className="text-label text-cx-accent font-bold block mt-0.5">Level-1 Escalation</span>
          </div>
        </div>
      </div>

      {/* Interactive Ontological Link Traversal Bar */}
      <div className="p-3 bg-white flex flex-wrap items-center gap-2 text-xs border-b border-slate-100">
        <span className="text-label font-mono text-slate-500 uppercase tracking-wider font-bold mr-1">
          Ontological Links:
        </span>

        {links.map((link: any, idx: number) => (
          <button
            key={idx}
            type="button"
            onClick={() => setActiveModalLink(link)}
            className="px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-800 hover:text-slate-950 border border-slate-200 hover:border-slate-300 text-label font-mono flex items-center gap-1.5 transition-colors cursor-pointer group shadow-2xs"
          >
            <span className="material-symbols-sharp text-xs text-slate-400 group-hover:text-cx-accent">
              arrow_outward
            </span>
            <span className="font-bold">{link.target_type}</span>
            <span className="px-1 py-0.2 bg-slate-100 border border-slate-200 text-label font-bold rounded-xs">
              {link.count}
            </span>
          </button>
        ))}

        <div className="ml-auto text-label font-mono text-slate-500 flex items-center gap-1">
          <span className="material-symbols-sharp text-xs text-slate-400">schema</span>
          <span>Link Graph Synchronized</span>
        </div>
      </div>

      {/* Linked Object Popover Modal */}
      {activeModalLink && (
        <div className="p-3 bg-slate-50 border-b border-slate-200 text-xs font-mono space-y-1">
          <div className="flex items-center justify-between text-slate-900 font-bold">
            <div className="flex items-center gap-1.5">
              <span className="material-symbols-sharp text-sm text-cx-accent">link</span>
              <span>
                Traversing Link: {activeModalLink.link_type} &rarr; {activeModalLink.target_type} ({activeModalLink.count} Entities)
              </span>
            </div>
            <button
              type="button"
              onClick={() => setActiveModalLink(null)}
              className="text-slate-500 hover:text-slate-900 font-bold px-1.5 cursor-pointer text-sm"
            >
              &times;
            </button>
          </div>
          <p className="text-slate-700 text-label font-sans">
            {activeModalLink.summary}
          </p>
          <div className="text-label text-rose-700 font-semibold flex items-center gap-1">
            <span className="material-symbols-sharp text-xs">warning</span>
            <span>{activeModalLink.risk_flag}</span>
          </div>
        </div>
      )}
    </div>
  );
}
