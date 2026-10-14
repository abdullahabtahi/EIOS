'use client';

/**
 * The radar's diagnostic inspector for one partner (spec 032). Every figure is a computed field of the radar row,
 * the backend what-if, or the partner's dossier deals; a value the platform did not compute shows as a dash.
 * Deals stage through the intent hub, so the shelf shows the card the hub signed.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import type { PartnerChurnItem, TradeOffCard, WhatIfCausalResponse } from '../state/cockpit-types';
import { useStageRequest } from './use-stage-request';

const DASH = '—';
const usd = (v: number | undefined) => (v === undefined ? DASH : `$${Math.round(v).toLocaleString()}`);
const pct = (v: number | undefined, digits = 1) => (v === undefined ? DASH : `${v > 0 ? '+' : ''}${v.toFixed(digits)}%`);

interface InspectorProps {
  partner: PartnerChurnItem;
  concession: number;
  onConcession: (value: number) => void;
  simulating: boolean;
  whatIf: WhatIfCausalResponse | null;
}

/** Hazard 30 days ago, 14 days ago and now, as scored by the pipeline at each date. */
function HazardPath({ partner }: { partner: PartnerChurnItem }) {
  const d = partner.historicalDrift;
  if (!d) return <p className="text-label text-cx-muted">No scoring history for this partner.</p>;
  const points = [d.tMinus30d.pChurn, d.tMinus14d.pChurn, partner.pChurn];
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${i * 150} ${30 - p * 28}`).join(' ');
  return (
    <div className="space-y-1">
      <svg className="w-full h-8 bg-cx-sub border border-cx-line" viewBox="0 0 300 32" preserveAspectRatio="none" aria-label="Churn hazard over 30 days">
        <path d={path} fill="none" stroke="currentColor" strokeWidth="2" className="text-cx-bad" />
      </svg>
      <div className="flex justify-between text-label text-cx-muted">
        <span>30 days ago {(points[0] * 100).toFixed(0)}%</span>
        <span>14 days ago {(points[1] * 100).toFixed(0)}%</span>
        <span>now {(points[2] * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-cx-sub p-1.5 border border-cx-line">
      <span className="text-label text-cx-muted block">{label}</span>
      <span className="font-bold text-cx-ink">{value}</span>
    </div>
  );
}

function WhatIf({ concession, onConcession, simulating, whatIf }: Omit<InspectorProps, 'partner'>) {
  return (
    <div className="p-3 bg-white border border-cx-line space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-bold text-label text-cx-ink">Retention what-if (hazard model)</span>
        {simulating && <span className="text-label text-cx-muted">Scoring…</span>}
      </div>
      <label className="block text-label text-cx-muted">
        Playbook intensity: <span className="font-bold text-cx-ink">{concession}%</span>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          value={concession}
          onChange={(e) => onConcession(Number(e.target.value))}
          className="w-full accent-cx-ink cursor-pointer h-1.5"
          aria-label="Concession Intensity Slider"
        />
      </label>
      {whatIf ? (
        <div className="p-2.5 bg-cx-sub border border-cx-line space-y-1 text-label">
          <div className="flex justify-between"><span>Projected drop in hazard</span><span className="font-bold">{pct(whatIf.projected_retention_lift_pct ?? undefined)}</span></div>
          <div className="flex justify-between"><span>Cost</span><span className="font-bold">{usd(whatIf.estimated_deal_cost_usd ?? undefined)}</span></div>
          <div className="flex justify-between"><span>Net over a quarter</span><span className="font-bold">{usd(whatIf.projected_net_margin_usd ?? undefined)}</span></div>
          <p className="text-cx-muted pt-1 border-t border-cx-line">{whatIf.governed_decision_rationale}</p>
        </div>
      ) : (
        <p className="text-label text-cx-muted">Move the slider to re-score this partner with the playbook applied.</p>
      )}
    </div>
  );
}

function Deals({ partner, deals }: { partner: PartnerChurnItem; deals: TradeOffCard[] | null }) {
  const { selectEntity } = useCockpit();
  const staging = useStageRequest();
  if (deals === null) {
    return (
      <button type="button" onClick={() => selectEntity(partner.partnerId)} className="w-full py-1.5 border border-cx-line text-label font-semibold cursor-pointer hover:bg-cx-sub">
        Open {partner.partnerId} to see its retention deals
      </button>
    );
  }
  if (deals.length === 0) return <p className="text-label text-cx-muted">No retention playbook applies to this partner&apos;s signals.</p>;
  return (
    <div className="space-y-2">
      {deals.map((d) => (
        <div key={d.proposedAction} className="p-2.5 bg-cx-sub border border-cx-line space-y-1.5">
          <div className="font-bold text-cx-ink">{d.proposedAction}</div>
          <div className="text-label text-cx-muted">{d.projectedReturn}</div>
          <div className="text-label text-cx-muted">{d.projectedRisk}</div>
          <div className="text-label text-cx-faint italic">{d.downsideSensitivity}</div>
          {d.stageRequest && (
            <button
              type="button"
              disabled={staging.busy}
              onClick={() => d.stageRequest && void staging.stage(d.stageRequest)}
              className="w-full py-1.5 bg-cx-ink hover:bg-cx-ink-hover text-white font-bold text-xs cursor-pointer"
            >
              Stage governed action ({partner.partnerId})
            </button>
          )}
        </div>
      ))}
      {staging.message && (
        <div role={staging.message.tone === 'error' ? 'alert' : 'status'} className={`text-label ${staging.message.tone === 'error' ? 'text-cx-bad' : 'text-cx-ok'}`}>
          {staging.message.text}
        </div>
      )}
    </div>
  );
}

export function PartnerRadarInspector(props: InspectorProps) {
  const { state } = useCockpit();
  const { partner } = props;
  const dossier = state.activeDossier;
  const deals = dossier?.entityId === partner.partnerId ? dossier.tradeOffs ?? [] : null;
  const pairs = partner.mirrorTradeCorrelation;
  return (
    <div className="space-y-3 font-mono text-xs text-cx-ink">
      <div className="p-3 bg-white border border-cx-line space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-bold text-sm">{partner.name} <span className="text-label text-cx-muted">{partner.partnerId}</span></span>
          <span className="text-label font-bold px-2 py-0.5 border border-cx-line">P(churn) {partner.pChurn.toFixed(2)}</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-label">
          <Tile label="30-day volume" value={usd(partner.valueAtRiskUsd)} />
          <Tile label="Expected days to churn" value={partner.daysToChurn ? `${partner.daysToChurn}` : DASH} />
          <Tile label="Change vs 30 days ago" value={pct(partner.historicalDrift?.driftVelocityPct, 0)} />
          <Tile label="Opposite-trading pair" value={pairs === undefined ? DASH : pairs > 0 ? `${(pairs * 100).toFixed(0)}% confidence` : 'none found'} />
        </div>
      </div>

      <div className="p-3 bg-white border border-cx-line space-y-2">
        <span className="font-bold text-label block">Hazard path and signals</span>
        <HazardPath partner={partner} />
        <div className="grid grid-cols-2 gap-2 text-label">
          <Tile label="Median payout time" value={partner.cashierLatencyHours === undefined ? DASH : `${partner.cashierLatencyHours.toFixed(1)} h`} />
          <Tile label="Rival named in messages" value={partner.competitorPoaching ?? 'none reported'} />
          <Tile label="Logins, 2 weeks vs 2 before" value={pct(partner.loginDecayPct)} />
          <Tile label="Negative messages" value={partner.supportTicketCount === undefined ? DASH : `${partner.supportTicketCount}`} />
        </div>
      </div>

      <WhatIf concession={props.concession} onConcession={props.onConcession} simulating={props.simulating} whatIf={props.whatIf} />

      <div className="p-3 bg-white border border-cx-line space-y-2">
        <span className="font-bold text-label block">Retention deals</span>
        <Deals partner={partner} deals={deals} />
      </div>

      <p className="text-label text-cx-muted">
        Playbook win rate: {partner.empiricalPlaybookWinRate === undefined ? 'no playbook outcomes recorded yet' : `${(partner.empiricalPlaybookWinRate * 100).toFixed(1)}%`}
      </p>
    </div>
  );
}
