/* eslint-disable @typescript-eslint/no-explicit-any */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET as getCase } from '@/app/api/cockpit/aml/cases/[entityId]/route';
import { GET as getWorkstation } from '@/app/api/cockpit/workstations/[role]/route';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const backendCase = {
  entity_id: 'CR91204',
  data_origin: 'engine',
  active_dossier: {
    dossier_id: 'dos_CR91204',
    entity_id: 'CR91204',
    headline: 'AML Investigation Dossier - Entity CR91204',
    executive_summary: 'Round-trip: deposit, near-zero trading, withdrawal inside 72 hours',
    sections: [
      {
        section_id: 'sec_velocity',
        title: 'Transaction Velocity & Discrepancy',
        narrative_text: 'Observed 30-day deposits $3,200.',
        citations: ['realized_deposit_volume_30d_usd'],
        metrics: [
          {
            metric_id: 'realized_deposit_volume_30d_usd',
            formatted_value: '$3,200',
            raw_value: 3200,
            origin_engine: 'EngineAMLService',
            steward_role: 'AMLComplianceSteward',
            citation: '[COMPUTED]',
          },
        ],
      },
    ],
  },
  kinetic_canvas: { canvas_type: 'TOPOLOGICAL_GRAPH', payload: { nodes: [], edges: [] } },
};

const ctx = (entityId: string) => ({ params: Promise.resolve({ entityId }) });
const get = (path: string) => new Request(`http://localhost:3000${path}`);

describe('AML case proxy: a selection opens that account, never a stand-in', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it('normalises the computed dossier and marks it as engine data', async () => {
    fetchMock.mockResolvedValue(json(200, backendCase));
    const res = await getCase(get('/api/cockpit/aml/cases/CR91204') as any, ctx('CR91204'));
    const body = await res.json();
    expect(res.status).toBe(200);
    expect(body.entityId).toBe('CR91204');
    expect(body.dataOrigin).toBe('engine');
    expect(body.activeDossier.entityId).toBe('CR91204');
    const metric = body.activeDossier.sections[0].metrics[0];
    expect(metric.formattedValue).toBe('$3,200');
    expect(metric.citation).toBe('[COMPUTED]');
  });

  it('relays an unknown account as 404 instead of inventing a dossier', async () => {
    fetchMock.mockResolvedValue(json(404, { detail: 'no such account' }));
    const res = await getCase(get('/api/cockpit/aml/cases/CR00000') as any, ctx('CR00000'));
    expect(res.status).toBe(404);
  });

  it('reports an unreachable backend as 503 offline', async () => {
    fetchMock.mockRejectedValue(new Error('connect ECONNREFUSED'));
    const res = await getCase(get('/api/cockpit/aml/cases/CR91204') as any, ctx('CR91204'));
    expect(res.status).toBe(503);
    expect((await res.json()).offline).toBe(true);
  });

  it('asks the backend for exactly the selected account, encoded', async () => {
    fetchMock.mockResolvedValue(json(200, backendCase));
    await getCase(get('/api/cockpit/aml/cases/a') as any, ctx('CR91204'));
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/cockpit/aml/cases/CR91204');
  });
});

describe('Workstation proxy: the [ENGINE] badge is the only way to engine origin', () => {
  const fetchMock = vi.fn();
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  const workstation = (badge: string) => ({
    fallback_state: { badge_label: badge },
    triage_queue: { items: [{ id: 'ALT-CR84920', title: 'AML', entity_id: 'CR84920', priority_score: 0.99 }] },
  });
  const call = (badge: string) =>
    getWorkstation(get('/api/cockpit/workstations/aml_investigator') as any, {
      params: Promise.resolve({ role: 'aml_investigator' }),
    });

  it.each([
    ['[ENGINE]', 'engine'],
    ['[LIVE]', 'live'],
    ['[ILLUSTRATIVE]', 'fixture'],
    ['[SOMETHING-ELSE]', 'fixture'],
  ])('maps %s to %s', async (badge, origin) => {
    fetchMock.mockResolvedValue(json(200, workstation(badge)));
    expect((await (await call(badge)).json()).dataOrigin).toBe(origin);
  });

  it('forwards the selected entity to the backend', async () => {
    fetchMock.mockResolvedValue(json(200, workstation('[ENGINE]')));
    await getWorkstation(get('/api/cockpit/workstations/aml_investigator?entity_id=CR91204') as any, {
      params: Promise.resolve({ role: 'aml_investigator' }),
    });
    expect(String(fetchMock.mock.calls[0][0])).toContain('entity_id=CR91204');
  });
});
