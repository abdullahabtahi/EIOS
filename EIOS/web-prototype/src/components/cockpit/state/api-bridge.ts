/**
 * EIOS Live Backend API Bridge (F019 Phase 2, T010).
 * Connects Cockpit React workstations to the FastAPI backend. Partner calls return null on failure; the AML graph
 * keeps its labelled replay, which engine-backed cases refuse.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
import { authFetch } from '@/lib/auth/token';

// Same-origin by default: the browser calls the /api/v1 proxy, which forwards to EIOS_BACKEND_URL, so a page and its
// data always come from the backend that page was started against. An explicit NEXT_PUBLIC_API_URL still wins.
export const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

/**
 * The partner churn radar from the backend, or null when it could not be read. Nothing is filled in on failure.
 */
export async function fetchChurnRadar(): Promise<any | null> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/churn/radar`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
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
 * A partner as an ontology object, or null when the backend could not provide it.
 */
export async function fetchPartnerOntology(partnerId: string): Promise<any | null> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/churn/partner/${encodeURIComponent(partnerId)}/ontology`);
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}

/**
 * A retention deal's projected effect from the backend's hazard model, or null when it could not be computed.
 */
export async function simulatePartnerWhatIf(partnerId: string, prompt: string): Promise<any | null> {
  try {
    const res = await authFetch(`${BACKEND_BASE_URL}/api/v1/churn/partner/${encodeURIComponent(partnerId)}/what-if`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ proposal_prompt: prompt }),
    });
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
