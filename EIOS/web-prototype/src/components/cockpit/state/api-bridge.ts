/**
 * EIOS Live Backend API Bridge & Native SSE Streaming Client (F019 Phase 2, T010).
 * Connects Cockpit React workstations to FastAPI backend with offline replay fallback.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
import {
  PersonaRole,
  WorkstationApiResponse,
} from './cockpit-types';
import { getFallbackWorkstationData } from './fixtures';
import { authFetch } from '@/lib/auth/token';
import { createSseParser } from '@/lib/sse';

// An explicit (even empty) NEXT_PUBLIC_API_URL wins; empty means same-origin, served by the /api/v1 gateway.
export const BACKEND_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== 'undefined' && window.location.hostname !== 'localhost'
    ? ''
    : 'http://localhost:8002');

export interface StreamSubscription {
  close: () => void;
}

/**
 * Server-Sent Events subscription over authenticated fetch (EventSource cannot send an
 * Authorization header). Reconnects with exponential backoff until closed.
 */
export function subscribeToSseStream<T>(
  endpoint: string,
  eventName: string,
  onData: (data: T) => void,
  onError?: (err: unknown) => void
): StreamSubscription {
  if (typeof window === 'undefined') {
    return { close: () => {} };
  }

  const url = `${BACKEND_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  let closed = false;

  const run = async () => {
    let delayMs = 1000;
    while (!closed) {
      try {
        const res = await authFetch(url, {
          headers: { Accept: 'text/event-stream' },
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error(`SSE stream HTTP ${res.status}`);
        delayMs = 1000;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        const feed = createSseParser((name, data) => {
          if (name !== eventName) return;
          try {
            onData(JSON.parse(data) as T);
          } catch (e) {
            console.warn(`[API Bridge SSE Parse Error] ${e}`);
          }
        });
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          feed(decoder.decode(value, { stream: true }));
        }
      } catch (err) {
        if (closed) return;
        if (onError) onError(err);
      }
      if (closed) return;
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      delayMs = Math.min(delayMs * 2, 30000);
    }
  };
  void run();

  return {
    close: () => {
      closed = true;
      controller.abort();
    },
  };
}

/**
 * Fetches live Partner Churn Radar dataset with fallback to mock fixtures.
 */
export async function fetchChurnRadar(): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/churn/radar`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using offline replay for Churn Radar:', err);
    return {
      as_of: new Date().toISOString(),
      aggregate_var_30d_usd: 1041600.0,
      monitored_partners_count: 3,
      high_risk_partners_count: 2,
      isReplay: true,
      partners: [
        {
          partner_id: 'AP-1029',
          realized_volume_30d_usd: 1240000.0,
          churn_hazard_probability: 0.84,
          quadrant: 'HIGH_VALUE_HIGH_RISK',
          days_to_intervention_deadline: 14,
          primary_root_cause: 'Payout ticket delays + rival spread comparison (Exness poaching)',
          login_decay_pct: -68.0,
          ftd_decay_pct: -45.0,
        },
      ],
    };
  }
}

/**
 * Fetches live Partner Fraud referral tree with sub-affiliate directed graph.
 */
export async function fetchFraudTree(partnerId = 'AP-1029'): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/fraud/tree?partner_id=${partnerId}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using offline replay for Fraud Tree:', err);
    return {
      master_partner_id: partnerId,
      tier: 'Tier 1 Regional Master',
      active_sub_affiliates_count: 14,
      total_clawback_exposure_usd: 63750.0,
      clawback_status: 'STAGED_FOR_GOVERNED_REVIEW [REPLAY]',
      isReplay: true,
    };
  }
}

/**
 * Fetches live AML Investigation Dossier.
 */
export async function fetchAmlDossier(caseId: string): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/aml/dossier/${caseId}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using offline replay for AML Dossier:', err);
    return {
      case_id: caseId,
      entity_id: 'CR84920',
      composite_risk_score: 89,
      isReplay: true,
      peer_group_comparison: {
        peer_cohort: 'Retail Traders (SG / Self-Employed)',
        median_turnover_usd: 720.0,
        entity_turnover_usd: 8000.0,
        standard_deviations_above_median: 4.82,
      },
    };
  }
}

/**
 * Fetches AML Relational Graph for hardware-accelerated Canvas / WebGL rendering.
 */
export async function fetchAmlGraph(caseId: string, hubThreshold = 100): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/aml/dossier/${caseId}/graph?hub_threshold=${hubThreshold}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using offline replay for AML Graph:', err);
    return {
      graph_id: `graph_${caseId}`,
      seed_entity_id: 'CR84920',
      total_uncollapsed_entities: 71,
      isReplay: true,
      nodes: [
        { node_id: 'CR84920', node_type: 'CLIENT_ACCOUNT', label: 'Suspect Account #CR84920', degree: 4 },
        { node_id: 'PA-HUB-007', node_type: 'PAYMENT_AGENT', label: 'Central Payment Gateway #007', degree: 142, is_hub_suppressed: true },
        { node_id: 'IP-CGNAT-GATEWAY-88', node_type: 'IP_ADDRESS', label: 'Carrier CGNAT Gateway 103.24.12.0/24', degree: 148, is_hub_suppressed: true },
      ],
      edges: [
        { source_node_id: 'CR84920', target_node_id: 'PA-HUB-007', edge_type: 'TRANSACTION_FLOW', transaction_volume_usd: 8000.0 },
      ],
    };
  }
}

/**
 * Executes Causal What-If Simulation via FastAPI with Hare-Niemeyer attribution.
 */
export async function executeWhatIfSimulation(shockParam: string, magnitudePct: number): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/synthesis/what-if`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ shock_param: shockParam, magnitude_pct: magnitudePct }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using offline replay for What-If:', err);
    return {
      simulation_id: `sim_replay_${Date.now()}`,
      shock_param: shockParam,
      magnitude_pct: magnitudePct,
      attribution_sum_pct: 100.0,
      isReplay: true,
      attribution_waterfall: [
        { driver_id: 'spread_elasticity', impact_pct: 42.5 },
        { driver_id: 'rebate_sensitivity', impact_pct: 35.5 },
        { driver_id: 'macro_volatility', impact_pct: 22.0 },
      ],
    };
  }
}

/**
 * Universal workstation loader with live bridge & replay fallback.
 */
export async function loadWorkstationData(role: PersonaRole): Promise<WorkstationApiResponse> {
  try {
    const res = await authFetch(`/api/cockpit/workstations/${role}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return {
      ...getFallbackWorkstationData(role),
      isLiveConnected: false,
      isCachedFallback: true,
    };
  }
}

export function getFallbackPartnerOntology(partnerId: string): any {
  return {
    object_type: 'Partner',
    primary_key: partnerId,
    security_markings: ['TLP:AMBER', 'COMMERCIAL_SENSITIVE'],
    lifecycle_state: 'AT_RISK_POACHING',
    schema_version: 'v2.1.0',
    hot_state_sha256: `SHA256:7f8a${partnerId.toLowerCase()}920485bf2d`,
    properties: {
      partner_id: partnerId,
      legal_name: 'Carlos Mendez (Alpha FX LatAm)',
      tier: 'TIER_1_SUPER',
      region_id: 'REG_LATAM_SOUTH',
      country: 'Colombia / Brazil',
      tenure_days: 842,
      value_at_risk_usd: 540000.0,
      hazard_probability_30d: 0.84,
      priority_score: 89.2,
      risk_tier: 'CRITICAL',
      intervention_window: '14D_RECOVERY_WINDOW',
      change_point_flag: true,
      active_traders_count: 1420,
      payout_rate_pct: 45.0,
      cashier_latency_sla_hours: 4.8,
      primary_synthetics_volume_pct: 68.5,
    },
    links: [
      { link_type: 'HAS_SUB_AFFILIATE', target_type: 'SubAffiliate', count: 14, summary: '14 Tier-2 Introducers' },
      { link_type: 'DRIVES_TRADERS', target_type: 'ClientAccount', count: 1420, summary: '940 Volatility 75 / 480 FX clients' },
      { link_type: 'HAS_SUPPORT_DISPUTES', target_type: 'ZendeskTicket', count: 3, summary: '2 P2P cashier delays, 1 rebate mismatch' },
      { link_type: 'COMPETITOR_POACHING', target_type: 'Competitor', count: 1, summary: 'Exness LatAm Zero-Swap Gold Campaign' },
    ],
    upstream_lineage: [
      'ClickHouse MT5 & Algo Trading Raw Deals',
      'dbt silver_partners_aggregation_daily',
      'DuckDB Hot-State Ledger (WORM Chained)',
      'Kinetic Partner Object (F019 v2.1.0)',
    ],
    allowed_action_types: [
      { action_type: 'DeployRetentionConcession', label: 'Deploy VIP Spread Rebate Concession' },
      { action_type: 'WhitelistDirectCashierRail', label: 'Whitelist Dedicated VIP P2P Cashier Rail' },
      { action_type: 'AllocateCoMarketingBudget', label: 'Allocate Bogotá Masterclass Co-Marketing Budget' },
    ],
  };
}

/**
 * Fetch canonical EIOS Ontology Object 360 representation of Partner entity.
 */
export async function fetchPartnerOntology(partnerId: string): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/churn/partner/${encodeURIComponent(partnerId)}/ontology`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using fallback Partner Object 360:', err);
    return getFallbackPartnerOntology(partnerId);
  }
}

export function getFallbackPartnerBattlecards(partnerId: string): any {
  return {
    partner_id: partnerId,
    synthesizer_model: 'gemini-3.8-flash',
    generated_at: new Date().toISOString(),
    forensic_diagnostic_narrative:
      'Gemini 3.8 Flash Multi-Signal Synthesis: Subject AP-1029 (Carlos Mendez, LatAm Master IB) is experiencing acute disengagement driven by a 4.8-hour latency spike on local DP2P cashier withdrawals in Colombia, compounded by aggressive rival poaching from Exness offering +$3/lot higher rebates on Gold. 3 of his Tier-2 sub-IBs have begun redirecting new trader traffic. Recovery window is active for 14 days before rival broker contractual terms lock.',
    battlecards: [
      {
        id: 'card_p2p_cashier',
        title: 'VIP Cashier Whitelist & Instant DP2P Clearing',
        angle: 'Operational Friction Removal & Relationship Trust',
        channel: 'WhatsApp / Telegram Voice Note',
        whatsapp_script:
          'Hola Carlos! Vi que tus traders tuvieron fricción con los retiros de P2P Cashier la semana pasada en Medellín. Ya hablé directo con nuestro equipo de tesorería LatAm y te habilitamos un canal VIP directo con 0% comisión y acreditación bancaria en menos de 15 minutos. Pruébalo hoy con tu equipo.',
        projected_lift_pct: 38.0,
        deal_cost_usd: 0.0,
        net_margin_usd: 42000.0,
        concession_bound: 'Pre-approved under Partner Manager Level-2 authority (Zero P&L cost)',
        action_type: 'WhitelistDirectCashierRail',
      },
      {
        id: 'card_spread_rebate',
        title: 'Volatility 75 & Crash 500 Spread Rebate Upgrade (+1.20/lot)',
        angle: 'Commercial Parity vs Exness Poaching',
        channel: 'WhatsApp Direct Proposal',
        whatsapp_script:
          'Carlos, para apoyarte contra las promos agresivas que están circulando en la región, te acabo de autorizar un upgrade especial en tu rebate: +$1.20 por lote operado en Volatility 75 y Crash 500 por los próximos 90 días. Con el volumen de tu comunidad, esto te representa +$14,000 USD adicionales sobre cualquier otra plataforma. ¿Te parece si lo activamos este lunes?',
        projected_lift_pct: 74.0,
        deal_cost_usd: 18000.0,
        net_margin_usd: 92000.0,
        concession_bound: 'Requires maintaining >= 50 monthly active traders; capped at 90 days. Net ROI: 5.1x',
        action_type: 'DeployRetentionConcession',
      },
      {
        id: 'card_seminar_sponsorship',
        title: 'Bogotá Trading Academy Sponsorship ($3,500 Budget)',
        angle: 'Community Retention & New Lead Acquisition',
        channel: 'WhatsApp / Phone Call',
        whatsapp_script:
          'Carlos, queremos patrocinar tu próximo masterclass presencial de trading en Bogotá. EIOS cubre $3,500 USD de salón, merchandising y welcome bonus para tus 150 nuevos alumnos verificados. Armemos la fecha juntos.',
        projected_lift_pct: 45.0,
        deal_cost_usd: 3500.0,
        net_margin_usd: 34000.0,
        concession_bound: 'Co-marketing budget pre-allocated in Q4 LatAm partner expansion pool',
        action_type: 'AllocateCoMarketingBudget',
      },
    ],
  };
}

/**
 * Fetch Gemini 3.8 Flash multi-signal forensic diagnostic narrative & WhatsApp/Telegram battlecards.
 */
export async function fetchPartnerBattlecards(partnerId: string): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/churn/partner/${encodeURIComponent(partnerId)}/battlecards`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using fallback Gemini 3.8 Flash Battlecards:', err);
    return getFallbackPartnerBattlecards(partnerId);
  }
}

/**
 * Evaluates partner retention counterfactual deal scenarios using Gemini 3.8 Flash and SCM.
 */
export async function simulatePartnerWhatIf(partnerId: string, prompt: string): Promise<any> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/churn/partner/${encodeURIComponent(partnerId)}/what-if`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ proposal_prompt: prompt }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.info('[API Bridge] Using fallback Gemini 3.8 Flash What-If:', err);
    return {
      partner_id: partnerId,
      evaluator_model: 'gemini-3.8-flash',
      evaluated_at: new Date().toISOString(),
      query_prompt: prompt,
      projected_retention_lift_pct: 74.0,
      confidence_interval_95: [66.0, 82.0],
      estimated_deal_cost_usd: 18000.0,
      projected_net_margin_usd: 92000.0,
      verdict: 'OPTIMAL_FRONTIER_APPROVED',
      governed_decision_rationale:
        'Gemini 3.8 Flash Causal Evaluation: Proposed concession lies on the optimal Pareto frontier. Delivers 74% retention lift with 5.1x net margin recovery ratio.',
      causal_refuter_p_value: 0.44,
    };
  }
}
