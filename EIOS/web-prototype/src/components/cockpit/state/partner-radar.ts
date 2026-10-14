/**
 * Partner radar data for the partner workstation (spec 032): the backend's computed radar in the cockpit's shape,
 * and the cohorts the cohort test found. A value the backend did not send stays undefined; nothing is filled in.
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { authFetch } from '@/lib/auth/token';
import type { PartnerChurnItem, StageRequest } from './cockpit-types';

const num = (v: unknown): number | undefined => (typeof v === 'number' && Number.isFinite(v) ? v : undefined);
const str = (v: unknown): string | undefined => (typeof v === 'string' && v ? v : undefined);

function drift(raw: any): PartnerChurnItem['historicalDrift'] {
  const d = raw?.historical_drift ?? raw?.historicalDrift;
  if (!d?.tMinus30d || !d?.tMinus14d) return undefined;
  return { tMinus30d: d.tMinus30d, tMinus14d: d.tMinus14d, driftVelocityPct: Number(d.driftVelocityPct ?? 0) };
}

/** One radar row from the backend's contract (snake_case) or an already-mapped item. */
export function toPartnerItem(raw: any): PartnerChurnItem {
  const id = String(raw.partner_id ?? raw.partnerId ?? '');
  return {
    partnerId: id,
    name: str(raw.name) ?? id,
    tier: (str(raw.tier) ?? 'TIER_3_AFFILIATE') as PartnerChurnItem['tier'],
    pChurn: num(raw.churn_hazard_probability ?? raw.pChurn) ?? 0,
    valueAtRiskUsd: num(raw.realized_volume_30d_usd ?? raw.valueAtRiskUsd) ?? 0,
    daysToChurn: num(raw.days_to_intervention_deadline ?? raw.daysToChurn) ?? 0,
    changePointDetected: Boolean(raw.change_point_flag ?? raw.changePointDetected),
    mirrorTradeCorrelation: num(raw.mirror_trade_correlation ?? raw.mirrorTradeCorrelation),
    extractedCommissionUsd: num(raw.extracted_commission_usd ?? raw.extractedCommissionUsd),
    region: str(raw.region),
    cohort: str(raw.cohort),
    loginDecayPct: num(raw.login_decay_pct ?? raw.loginDecayPct),
    referralDropWoWPct: num(raw.ftd_decay_pct ?? raw.referralDropWoWPct),
    cashierLatencyHours: num(raw.cashier_latency_sla_hours ?? raw.cashierLatencyHours),
    supportTicketCount: num(raw.support_ticket_count ?? raw.supportTicketCount),
    competitorPoaching: str(raw.competitor_poaching ?? raw.competitorPoaching),
    primaryDriver: str(raw.primary_driver ?? raw.primaryDriver),
    primaryRootCause: str(raw.primary_root_cause ?? raw.primaryRootCause),
    projectedLiftPct: num(raw.projected_lift_pct ?? raw.projectedLiftPct),
    netMarginRecoveryUsd: num(raw.net_margin_recovery_usd ?? raw.netMarginRecoveryUsd),
    empiricalPlaybookWinRate: num(raw.empirical_win_rate ?? raw.empiricalPlaybookWinRate),
    historicalDrift: drift(raw),
  };
}

/** The radar the workstation payload carries on the engine plane, or null when it carries none. */
export function partnersFromCanvas(canvas: { type?: string; data?: any } | null | undefined): PartnerChurnItem[] | null {
  const rows = canvas?.type === 'CHURN_RADAR' ? canvas.data?.partners : null;
  return Array.isArray(rows) && rows.length ? rows.map(toPartnerItem) : null;
}

export interface CohortSignal {
  cohortId: string;
  region: string;
  partnerCount: number;
  valueAtRiskUsd: number;
  medianHazard?: number;
  pValue: number;
  primaryDriver: string;
  partnerIds: string[];
  stageRequest: StageRequest | null;
}

function toCohort(raw: any): CohortSignal {
  return {
    cohortId: String(raw.cohort_id ?? ''),
    region: String(raw.region ?? ''),
    partnerCount: num(raw.partner_count) ?? 0,
    valueAtRiskUsd: num(raw.aggregate_value_at_risk_usd) ?? 0,
    medianHazard: num(raw.median_hazard),
    pValue: num(raw.p_value) ?? 1,
    primaryDriver: String(raw.primary_driver ?? ''),
    partnerIds: Array.isArray(raw.affected_partner_ids) ? raw.affected_partner_ids.map(String) : [],
    stageRequest: raw.stage_request ?? null,
  };
}

/** Regional cohorts the backend's cohort test found; empty when there are none or they could not be read. */
export async function fetchCohorts(): Promise<CohortSignal[]> {
  try {
    const res = await authFetch('/api/v1/churn/cohorts', { headers: { Accept: 'application/json' } });
    if (!res.ok) return [];
    const body = await res.json();
    return Array.isArray(body?.cohorts) ? body.cohorts.filter((c: any) => c?.stage_request !== undefined).map(toCohort) : [];
  } catch {
    return [];
  }
}
