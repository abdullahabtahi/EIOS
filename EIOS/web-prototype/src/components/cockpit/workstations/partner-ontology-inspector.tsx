'use client';

/**
 * The selected partner as an ontology object (spec 032): its computed properties, the objects it links to, the
 * engines and data products behind it, and the actions it allows. Read from the backend; a failed load says so.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import { fetchPartnerOntology } from '../state/api-bridge';

/* eslint-disable @typescript-eslint/no-explicit-any */
type Load = { status: 'loading' } | { status: 'error' } | { status: 'ready'; data: any };

const DASH = '—';
const fmt = {
  usd: (v: unknown) => (typeof v === 'number' ? `$${Math.round(v).toLocaleString()}` : DASH),
  pct: (v: unknown) => (typeof v === 'number' ? `${v > 0 ? '+' : ''}${v.toFixed(1)}%` : DASH),
  ratio: (v: unknown) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : DASH),
  hours: (v: unknown) => (typeof v === 'number' ? `${v.toFixed(1)} h` : DASH),
  days: (v: unknown) => (typeof v === 'number' ? `${v} days` : DASH),
};

function Property({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2 bg-white border border-cx-line">
      <span className="text-label text-cx-muted block">{label}</span>
      <div className="font-bold text-cx-ink mt-0.5">{value}</div>
    </div>
  );
}

export function PartnerOntologyInspector() {
  const { state } = useCockpit();
  const partnerId = state.activeEntityId || state.activeTriageItemId?.replace('item_', '') || '';
  const [load, setLoad] = React.useState<Load>({ status: 'loading' });
  const [openLink, setOpenLink] = React.useState<any | null>(null);

  React.useEffect(() => {
    if (!partnerId) return;
    let active = true;
    setLoad({ status: 'loading' });
    setOpenLink(null);
    fetchPartnerOntology(partnerId).then((data) => {
      if (active) setLoad(data ? { status: 'ready', data } : { status: 'error' });
    });
    return () => {
      active = false;
    };
  }, [partnerId]);

  if (!partnerId) return <p className="p-4 text-xs text-cx-muted">Select a partner to see its object.</p>;
  if (load.status === 'loading') {
    return <p className="p-4 text-xs text-cx-muted bg-cx-sub border border-cx-line">Loading partner {partnerId}…</p>;
  }
  if (load.status === 'error') {
    return (
      <p role="alert" className="p-4 text-xs text-cx-bad bg-white border border-cx-line">
        The partner object for {partnerId} could not be loaded.
      </p>
    );
  }

  const o = load.data;
  const p = o.properties ?? {};
  const links: any[] = o.links ?? [];
  const actions: any[] = o.allowed_action_types ?? [];
  return (
    <div className="bg-white border border-cx-line shadow-sm text-cx-ink">
      <div className="p-3.5 bg-cx-ink text-white flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap font-mono text-xs">
          <span className="material-symbols-sharp text-base">hub</span>
          <span className="font-bold">{p.partner_id ?? partnerId}</span>
          <span className="font-sans">{p.name ?? p.legal_name ?? ''}</span>
          {(o.security_markings ?? []).map((m: string) => (
            <span key={m} className="px-1.5 py-0.5 border border-white/40 text-label font-bold">{m}</span>
          ))}
          {o.lifecycle_state && <span className="px-1.5 py-0.5 border border-white/40 text-label font-bold">{o.lifecycle_state}</span>}
        </div>
        {o.as_of && <span className="text-label font-mono opacity-80">as of {String(o.as_of).slice(0, 16).replace('T', ' ')} UTC</span>}
      </div>

      <div className="p-3.5 bg-cx-sub border-b border-cx-line">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 font-mono text-xs">
          <Property label="30-day volume" value={fmt.usd(p.realized_volume_30d_usd ?? p.value_at_risk_usd)} />
          <Property label="30-day churn hazard" value={fmt.ratio(p.hazard_probability_30d)} />
          <Property label="Expected days to churn" value={fmt.days(p.days_to_intervention_deadline)} />
          <Property label="Logins, 2 weeks vs 2 before" value={fmt.pct(p.login_decay_pct)} />
          <Property label="Median payout time" value={fmt.hours(p.payout_latency_hours ?? p.cashier_latency_sla_hours)} />
          <Property label="Payout time, 4 weeks before" value={fmt.hours(p.baseline_payout_latency_hours)} />
        </div>
      </div>

      <div className="p-3 flex flex-wrap items-center gap-2 text-xs border-b border-cx-line">
        <span className="text-label font-mono text-cx-muted font-bold mr-1">Links:</span>
        {links.map((link, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => setOpenLink(link)}
            className="px-2.5 py-1 bg-white hover:bg-cx-sub border border-cx-line text-label font-mono flex items-center gap-1.5 cursor-pointer"
          >
            <span className="font-bold">{link.target_type}</span>
            <span className="px-1 bg-cx-sub border border-cx-line font-bold">{link.count}</span>
          </button>
        ))}
      </div>

      {openLink && (
        <div className="p-3 bg-cx-sub border-b border-cx-line text-xs font-mono space-y-1">
          <div className="flex items-center justify-between font-bold">
            <span>{openLink.link_type} → {openLink.target_type} ({openLink.count})</span>
            <button type="button" onClick={() => setOpenLink(null)} className="px-1.5 cursor-pointer text-sm" aria-label="Close link">
              &times;
            </button>
          </div>
          <p className="text-label font-sans text-cx-muted">{openLink.summary}</p>
        </div>
      )}

      <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-3 text-label font-mono">
        <div>
          <span className="font-bold block mb-1">Computed from</span>
          <span className="text-cx-muted">{(o.upstream_lineage ?? []).join(' → ') || DASH}</span>
        </div>
        <div>
          <span className="font-bold block mb-1">Allowed actions</span>
          {actions.length === 0 ? (
            <span className="text-cx-muted">none for this partner&apos;s signals</span>
          ) : (
            <ul className="space-y-0.5">
              {actions.map((a) => (
                <li key={a.action_type + a.label}>
                  {a.label} <span className="text-cx-muted">({a.action_type}{a.requires_four_eyes ? ', two approvers' : ''})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
