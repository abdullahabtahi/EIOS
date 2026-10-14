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
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(sub.id)}
        className="w-full p-2 bg-white border border-cx-line hover:bg-cx-sub flex flex-wrap items-center justify-between gap-2 text-left cursor-pointer"
      >
        <span>
          <span className="font-bold text-cx-ink">{sub.name}</span> <span className="text-label text-cx-muted">[{sub.id}]</span>
          {sub.flagged_mirror_trading && <span className="ml-2 text-label font-bold text-cx-bad">opposite-trading pair</span>}
        </span>
        <span className="text-label text-cx-muted">
          {usd(sub.volume_usd)} 30-day volume
          {sub.churn_hazard_probability !== undefined && `, hazard ${(sub.churn_hazard_probability * 100).toFixed(0)}%`}
        </span>
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
          <h3 className="text-title font-sans font-semibold text-cx-ink">
            Referral network: {tree.name ?? tree.master_partner_id} [{tree.master_partner_id}]
          </h3>
          <p className="text-label text-cx-muted mt-0.5">
            {subs.length} sub-affiliates
            {tree.active_sub_affiliates_count !== undefined && ` (${tree.active_sub_affiliates_count} active in the last two weeks)`}
            {tree.referred_client_count !== undefined && `, ${tree.referred_client_count} referred clients`}
          </p>
        </div>
      </div>

      <section aria-label="Opposite-trading pairs" className="space-y-2">
        <h4 className="text-label font-bold text-cx-ink">Opposite-trading pairs</h4>
        {rings.length === 0 ? (
          <p className="text-label text-cx-muted">No opposite-trading pair found across this partner&apos;s network.</p>
        ) : (
          rings.map((r) => <RingCard key={r.ring_id} ring={r} />)
        )}
        {tree.statement && <p className="text-label text-cx-faint italic">{tree.statement}</p>}
      </section>

      <section aria-label="AML cases among referrals" className="space-y-1">
        <h4 className="text-label font-bold text-cx-ink">AML cases among referred clients</h4>
        {exposure.length === 0 ? (
          <p className="text-label text-cx-muted">No prioritised AML case among this partner&apos;s referrals.</p>
        ) : (
          <ul className="space-y-1 text-label font-mono">
            {exposure.map((x) => (
              <li key={x.alert_id} className="p-2 bg-cx-sub border border-cx-line">
                {x.alert_id}: {x.typology.replace(/_/g, ' ').toLowerCase()}, risk {x.risk_score}/100,
                {' '}{x.referred_members} of {x.ring_size} accounts referred here
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Sub-affiliates" className="space-y-1">
        <h4 className="text-label font-bold text-cx-ink">Sub-affiliates</h4>
        {subs.length === 0 ? (
          <p className="text-label text-cx-muted">This partner has no sub-affiliates.</p>
        ) : (
          <ul className="space-y-1 text-xs font-mono">
            {subs.map((s) => (
              <SubAffiliateRow key={s.id} sub={s} onOpen={selectEntity} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
