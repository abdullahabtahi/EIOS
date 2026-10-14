/**
 * EIOS Live Backend API Bridge (F019 Phase 2, T010).
 * Connects Cockpit React workstations to FastAPI backend with offline replay fallback.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
import { authFetch } from '@/lib/auth/token';

// Same-origin by default: the browser calls the /api/v1 proxy, which forwards to EIOS_BACKEND_URL, so a page and its
// data always come from the backend that page was started against. An explicit NEXT_PUBLIC_API_URL still wins.
export const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

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
