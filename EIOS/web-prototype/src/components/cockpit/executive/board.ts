/**
 * The executive board and the what-if, as the backend computed them (spec 034).
 *
 * Nothing here fills a gap: a failed read returns null and the screen says so; a refused shock returns the backend's
 * reason. Field names are the backend's, read once into camelCase.
 */
import type { StageRequest } from '../state/cockpit-types';
import { authFetch } from '@/lib/auth/token';

/* eslint-disable @typescript-eslint/no-explicit-any */
type Raw = Record<string, any>;

export interface Horizon {
  name: string;
  headline: string;
  metricId: string;
  value: number;
  figure: string;
  deltaPct: number;
  definitionVersion: string;
  asOf: string;
  source: string;
  owner: string;
}

export interface BoardRisk {
  id: string;
  title: string;
  severity: string;
  exposureUsd: number;
}

export interface BoardOpportunity {
  id: string;
  title: string;
  upsideUsd: number;
  actionType: string;
  stage: StageRequest | null;
}

export interface BoardForecast {
  point: number;
  low: number | null;
  high: number | null;
  nominal: number | null;
  coverage: number | null;
  skill: number | null;
  origins: number | null;
  horizonDays: number | null;
  deltaPct: number;
  assumption: string | null;
}

export interface GraphNode {
  id: string;
  label: string;
  domain: string;
  value: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
  confidence: number;
  placeboP: number;
  verified: boolean;
  label: string;
}

export interface Shock {
  id: string;
  label: string;
  driver: string;
}

export interface ExecutiveBoard {
  dataOrigin: string;
  asOf: string;
  horizons: Horizon[];
  risks: BoardRisk[];
  opportunities: BoardOpportunity[];
  forecast: BoardForecast;
  nodes: GraphNode[];
  edges: GraphEdge[];
  shocks: Shock[];
}

export interface Mitigation {
  playbookId: string;
  title: string;
  region: string;
  partners: number;
  costUsd: number;
  marginKeptUsd: number;
}

export interface Simulation {
  revenueImpactUsd: number;
  intervalLowUsd: number;
  intervalHighUsd: number;
  churnDeltaPct: number;
  firstDepositDeltaPct: number;
  attribution: { driver: string; pct: number }[];
  attributionSum: number;
  serverMs: number;
  extrapolates: boolean;
  causalLabel: string | null;
  causalReason: string | null;
  mitigations: Mitigation[];
  mitigationBasis: string | null;
}

export function normalizeBoard(raw: Raw): ExecutiveBoard {
  const figures: Raw = raw.figures ?? {};
  const stage: Raw = raw.stage_requests ?? {};
  const f: Raw = raw.forecast ?? {};
  return {
    dataOrigin: String(raw.data_origin ?? ''),
    asOf: String(raw.as_of ?? ''),
    horizons: (raw.briefing?.horizons ?? []).map((h: Raw) => ({
      name: h.horizon_name,
      headline: h.headline,
      metricId: h.primary_metric_id,
      value: h.observed_value,
      figure: figures[h.horizon_name] ?? String(h.observed_value),
      deltaPct: h.delta_period_pct,
      definitionVersion: h.provenance?.definition_version ?? '',
      asOf: h.provenance?.as_of_timestamp ?? '',
      source: h.provenance?.computation_source ?? '',
      owner: h.provenance?.owner_role ?? '',
    })),
    risks: (raw.briefing?.risks ?? []).map((r: Raw) => ({
      id: r.risk_id,
      title: r.title,
      severity: r.severity,
      exposureUsd: r.exposure_usd,
    })),
    opportunities: (raw.briefing?.opportunities ?? []).map((o: Raw) => ({
      id: o.opportunity_id,
      title: o.title,
      upsideUsd: o.projected_upside_usd,
      actionType: o.recommended_action_type,
      stage: (stage[o.opportunity_id] as StageRequest | undefined) ?? null,
    })),
    forecast: {
      point: f.point_estimate,
      low: f.interval_low ?? null,
      high: f.interval_high ?? null,
      nominal: f.interval_nominal ?? null,
      coverage: f.interval_coverage ?? null,
      skill: f.skill_vs_persistence ?? null,
      origins: f.backtest_origins ?? null,
      horizonDays: f.horizon_days ?? null,
      deltaPct: f.delta_period_pct,
      assumption: f.assumption ?? null,
    },
    nodes: (raw.dag?.nodes ?? []).map((n: Raw) => ({
      id: n.node_id,
      label: n.label,
      domain: n.domain,
      value: n.current_value,
    })),
    edges: (raw.dag?.edges ?? []).map((e: Raw) => ({
      source: e.source_node_id,
      target: e.target_node_id,
      weight: e.weight,
      confidence: e.refuter?.confidence ?? 0,
      placeboP: e.refuter?.placebo_p_value ?? 0,
      verified: Boolean(e.refuter?.is_causal_verified),
      label: e.refuter?.status_label ?? '',
    })),
    shocks: (raw.shocks ?? []).map((s: Raw) => ({ id: s.id, label: s.label, driver: s.driver })),
  };
}

export function normalizeSimulation(raw: Raw): Simulation {
  const ci: number[] = [...(raw.confidence_interval ?? [0, 0])].sort((a, b) => a - b);
  const changes: Raw = raw.projected_changes ?? {};
  return {
    revenueImpactUsd: changes.projected_revenue_impact_usd ?? 0,
    intervalLowUsd: ci[0],
    intervalHighUsd: ci[1],
    churnDeltaPct: changes.partner_churn_delta_pct ?? 0,
    firstDepositDeltaPct: changes.first_deposit_delta_pct ?? 0,
    attribution: (raw.attribution_waterfall ?? []).map((a: Raw) => ({ driver: a.driver, pct: a.contribution_pct })),
    attributionSum: raw.attribution_sum_pct ?? 0,
    serverMs: raw.latency_ms ?? 0,
    extrapolates: Boolean(raw.extrapolates_beyond_history),
    causalLabel: raw.causal_label ?? null,
    causalReason: raw.causal_reason ?? null,
    mitigations: (raw.mitigations ?? []).map((m: Raw) => ({
      playbookId: m.playbook_id,
      title: m.title,
      region: m.target_region,
      partners: m.partners,
      costUsd: m.estimated_cost_usd,
      marginKeptUsd: m.projected_margin_kept_usd,
    })),
    mitigationBasis: raw.mitigation_basis ?? null,
  };
}

function isBoard(raw: Raw | null): boolean {
  const f = raw?.forecast;
  return (
    Array.isArray(raw?.briefing?.horizons) &&
    typeof f?.point_estimate === 'number' &&
    typeof f?.delta_period_pct === 'number' &&
    Array.isArray(raw?.dag?.nodes)
  );
}

/** The board, or null when it could not be read. */
export async function fetchExecutiveBoard(): Promise<ExecutiveBoard | null> {
  try {
    const res = await authFetch('/api/cockpit/executive', { headers: { Accept: 'application/json' } });
    if (!res.ok) return null;
    const raw = await res.json();
    return isBoard(raw) ? normalizeBoard(raw) : null; // anything that is not a board is a failed read, not a board
  } catch {
    return null;
  }
}

export type SimulationOutcome = { ok: true; result: Simulation } | { ok: false; reason: string };

/** One shock through the engine. A refusal carries the backend's own reason. */
export async function simulateShock(shock: string, magnitudePct: number): Promise<SimulationOutcome> {
  try {
    const res = await authFetch('/api/cockpit/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ shock_param: shock, magnitude_pct: magnitudePct }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      const reason = typeof body.detail === 'string' ? body.detail : `The simulation failed (HTTP ${res.status}).`;
      return { ok: false, reason };
    }
    return { ok: true, result: normalizeSimulation(body) };
  } catch {
    return { ok: false, reason: 'The EIOS backend could not be reached. Nothing was simulated.' };
  }
}

export const usd = (v: number): string => `${v < 0 ? '-' : ''}$${Math.abs(Math.round(v)).toLocaleString('en-US')}`;
export const signed = (v: number, digits = 1): string => `${v > 0 ? '+' : ''}${v.toFixed(digits)}`;
