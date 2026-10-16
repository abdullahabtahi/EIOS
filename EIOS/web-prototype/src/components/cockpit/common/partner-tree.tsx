'use client';

/**
 * The selected partner's referral network (spec 032): its sub-affiliates with their volume and hazard, the
 * opposite-trading pairs the pair detector found across them, and AML cases among the partner's referrals.
 * Read from the workstation canvas; a clawback stages through the intent hub. Nothing here is drawn from samples.
 */

import * as React from 'react';
import { useCockpit } from '../state/cockpit-context';
import type { StageRequest } from '../state/cockpit-types';
import { useStageRequest } from './use-stage-request';

/* eslint-disable @typescript-eslint/no-explicit-any */
interface SubAffiliate {
  id: string;
  name: string;
  tier?: string;
  volume_usd?: number;
  churn_hazard_probability?: number;
  co_occurrence_pct?: number;
  flagged_mirror_trading?: boolean;
}

interface Ring {
  ring_id: string;
  scheme: string;
  paired_accounts: string[];
  partners?: string[];
  matched_timing_seconds?: number;
  unearned_commission_liability_usd?: number;
  co_occurrences?: number;
  collusion_confidence?: number;
}

interface AmlExposure {
  alert_id: string;
  entity_id: string;
  ring_size: number;
  referred_members: number;
  risk_score: number;
  typology: string;
}

interface AffiliateTree {
  master_partner_id: string;
  name?: string;
  tier?: string;
  active_sub_affiliates_count?: number;
  referred_client_count?: number;
  sub_affiliates?: SubAffiliate[];
  detected_abusive_rings?: Ring[];
  aml_exposure?: AmlExposure[];
  statement?: string;
}

const usd = (v?: number) => (v === undefined ? '—' : `$${Math.round(v).toLocaleString()}`);

/** A clawback of the commission a pair earned, against the sub-affiliate that referred its first account. */
function clawbackRequest(ring: Ring): StageRequest | null {
  const partner = ring.partners?.[0];
  if (!partner || !ring.unearned_commission_liability_usd) return null;
  return {
    action_type: 'ClawbackCommission',
    target_entity_id: partner,
    severity: 'HIGH',
    requires_four_eyes: true,
    metadata: { partner_id: partner, period: 'last 14 days', amount: ring.unearned_commission_liability_usd, evidence: ring.ring_id },
  };
}

function RingCard({ ring }: { ring: Ring }) {
  const staging = useStageRequest();
  const request = clawbackRequest(ring);
  return (
    <div className="p-3 bg-cx-sub border border-cx-line space-y-1.5 text-xs font-mono">
      <div className="font-bold text-cx-ink">{ring.scheme}</div>
      <div className="text-label text-cx-muted">
        Accounts {ring.paired_accounts.join(' and ')} under {ring.partners?.join(' and ') ?? '—'}
      </div>
      <div className="text-label text-cx-muted">
        {ring.co_occurrences ?? '—'} matched trades, median gap {ring.matched_timing_seconds?.toFixed(1) ?? '—'} s,
        confidence {ring.collusion_confidence === undefined ? '—' : `${(ring.collusion_confidence * 100).toFixed(0)}%`},
        commission earned {usd(ring.unearned_commission_liability_usd)}
      </div>
      {request && (
        <button
          type="button"
          disabled={staging.busy}
          onClick={() => void staging.stage(request)}
          className="px-3 py-1.5 bg-cx-ink hover:bg-cx-ink-hover text-white font-semibold text-xs cursor-pointer"
        >
          Stage commission clawback ({usd(ring.unearned_commission_liability_usd)})
        </button>
      )}
      {staging.message && (
        <div role={staging.message.tone === 'error' ? 'alert' : 'status'} className={`text-label ${staging.message.tone === 'error' ? 'text-cx-bad' : 'text-cx-ok'}`}>
          {staging.message.text}
        </div>
      )}
    </div>
  );
}

function SubAffiliateRow({ sub, onOpen }: { sub: SubAffiliate; onOpen: (id: string) => void }) {
  const hazard = sub.churn_hazard_probability;
  const isCritical = hazard !== undefined && hazard >= 0.7;
  const isHigh = hazard !== undefined && hazard >= 0.3 && hazard < 0.7;

  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(sub.id)}
        className="w-full p-2.5 bg-white border border-cx-line hover:border-blue-400 hover:bg-blue-50/20 flex flex-wrap items-center justify-between gap-3 text-left cursor-pointer transition-colors group shadow-2xs"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="material-symbols-sharp text-sm text-slate-400 group-hover:text-blue-700 transition-colors">
            account_circle
          </span>
          <div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-bold text-cx-ink group-hover:text-blue-700 transition-colors font-sans">
                {sub.name}
              </span>
              <span className="text-label font-mono text-cx-muted bg-slate-50 px-1 py-0.2 border border-slate-200">
                {sub.id}
              </span>
              {sub.flagged_mirror_trading && (
                <span className="text-label font-mono font-bold bg-red-50 text-red-700 border border-red-200 px-1.5 py-0.2">
                  opposite-trading pair
                </span>
              )}
            </div>
            <div className="text-label text-cx-muted font-mono mt-0.5">
              30D Volume: <strong className="text-slate-800">{usd(sub.volume_usd)}</strong>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {hazard !== undefined ? (
            <span
              className={`text-label font-mono px-2 py-0.5 border font-bold ${
                isCritical
                  ? 'bg-red-50 text-red-800 border-red-200'
                  : isHigh
                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                  : 'bg-green-50 text-green-800 border-green-200'
              }`}
            >
              HAZARD {(hazard * 100).toFixed(0)}%
            </span>
          ) : null}
          <span className="material-symbols-sharp text-base text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-0.5">
            chevron_right
          </span>
        </div>
      </button>
    </li>
  );
}

export function PartnerTree() {
  const { state, selectEntity } = useCockpit();
  const canvas = state.canvasPayload;
  const tree: AffiliateTree | undefined = canvas?.type === 'CHURN_RADAR' ? (canvas.data as any)?.affiliate_tree : undefined;

  if (!tree) {
    return <p className="p-4 text-xs text-cx-muted bg-white border border-cx-line">Select a partner to see its referral network.</p>;
  }
  const subs = tree.sub_affiliates ?? [];
  const rings = tree.detected_abusive_rings ?? [];
  const exposure = tree.aml_exposure ?? [];

  return (
    <div className="bg-white border border-cx-line p-4 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cx-line pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-sharp text-base text-blue-700">account_tree</span>
            <h3 className="text-title font-sans font-semibold text-cx-ink">
              Referral network: {tree.name ?? tree.master_partner_id} [{tree.master_partner_id}]
            </h3>
          </div>
          <p className="text-label text-cx-muted mt-0.5 font-mono">
            {subs.length} sub-affiliates
            {tree.active_sub_affiliates_count !== undefined && ` (${tree.active_sub_affiliates_count} active in the last two weeks)`}
            {tree.referred_client_count !== undefined && `, ${tree.referred_client_count} referred clients`}
          </p>
        </div>
      </div>

      {/* Surveillance & Integrity Dual Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Opposite-Trading Wash Surveillance */}
        <section aria-label="Opposite-trading pairs" className="p-3 bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-cx-ink flex items-center gap-1.5 font-sans">
              <span className={`material-symbols-sharp text-sm ${rings.length > 0 ? 'text-red-600' : 'text-green-700'}`}>
                {rings.length > 0 ? 'warning' : 'verified_user'}
              </span>
              Opposite-trading pairs
            </h4>
            <span className={`text-label font-mono px-1.5 py-0.2 border font-bold ${rings.length > 0 ? 'bg-red-50 text-red-800 border-red-200' : 'bg-green-50 text-green-800 border-green-200'}`}>
              {rings.length > 0 ? `${rings.length} FLAGGED` : 'VERIFIED CLEAN'}
            </span>
          </div>

          {rings.length === 0 ? (
            <div className="space-y-1">
              <p className="text-label text-cx-muted font-sans">
                No opposite-trading pair found across this partner&apos;s network.
              </p>
              {tree.statement && <p className="text-label text-cx-faint italic font-sans">{tree.statement}</p>}
            </div>
          ) : (
            <div className="space-y-2">
              {rings.map((r) => <RingCard key={r.ring_id} ring={r} />)}
              {tree.statement && <p className="text-label text-cx-faint italic font-sans">{tree.statement}</p>}
            </div>
          )}
        </section>

        {/* AML Surveillance */}
        <section aria-label="AML cases among referrals" className="p-3 bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-cx-ink flex items-center gap-1.5 font-sans">
              <span className={`material-symbols-sharp text-sm ${exposure.length > 0 ? 'text-red-600' : 'text-green-700'}`}>
                {exposure.length > 0 ? 'gavel' : 'shield'}
              </span>
              AML cases among referred clients
            </h4>
            <span className={`text-label font-mono px-1.5 py-0.2 border font-bold ${exposure.length > 0 ? 'bg-red-50 text-red-800 border-red-200' : 'bg-green-50 text-green-800 border-green-200'}`}>
              {exposure.length > 0 ? `${exposure.length} DETECTED` : 'VERIFIED CLEAR'}
            </span>
          </div>

          {exposure.length === 0 ? (
            <p className="text-label text-cx-muted font-sans">
              No prioritised AML case among this partner&apos;s referrals.
            </p>
          ) : (
            <ul className="space-y-1 text-label font-mono">
              {exposure.map((x) => (
                <li key={x.alert_id} className="p-2 bg-white border border-red-200 text-slate-800">
                  <span className="font-bold text-red-700">{x.alert_id}:</span> {x.typology.replace(/_/g, ' ').toLowerCase()}, risk {x.risk_score}/100,
                  {' '}{x.referred_members} of {x.ring_size} accounts referred here
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Sub-affiliates downline */}
      <section aria-label="Sub-affiliates" className="space-y-2 pt-1">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-cx-ink flex items-center gap-1.5 font-sans">
            <span className="material-symbols-sharp text-sm text-blue-700">group</span>
            Sub-affiliates
          </h4>
          <span className="text-label font-mono text-slate-500">
            {subs.length} active downlines
          </span>
        </div>

        {subs.length === 0 ? (
          <p className="text-label text-cx-muted bg-slate-50 p-3 border border-slate-200">
            This partner has no sub-affiliates.
          </p>
        ) : (
          <ul className="space-y-1.5 text-xs font-mono">
            {subs.map((s) => (
              <SubAffiliateRow key={s.id} sub={s} onOpen={selectEntity} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
