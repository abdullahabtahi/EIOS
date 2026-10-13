import { describe, it, expect } from 'vitest';
import { buildOperationsView } from '@/components/cockpit/state/operations-view-model';

const backendPayload = {
  sla_statuses: [
    {
      product_name: 'client_transactions',
      contract_schema_version: 'v2.1.0',
      row_count: 1854200,
      null_check_pass_rate: 0.9998,
      last_ingestion_timestamp: '2026-10-12T05:55:38.503341+00:00',
      freshness_sla_seconds: 300,
      status: 'BREACHED',
      is_degraded: true,
    },
    {
      product_name: 'transactions_aml',
      null_check_pass_rate: 0.9999,
      last_ingestion_timestamp: '2026-10-12T05:55:38.503341+00:00',
      freshness_sla_seconds: 180,
      status: 'HEALTHY',
    },
  ],
  error_budgets: [
    { slo_id: 'SLO-1', name: 'Streaming Ingestion Lag (<30s)', consumed_pct: 24.2, status: 'HEALTHY' },
  ],
  red_line_gates: [
    { gate_id: 'RL-1', name: 'Metric Calculation Determinism', status: 'PASS', margin_delta: 0 },
    { gate_id: 'RL-2', name: 'Four-Eyes Enforcement Integrity', status: 'FAIL', margin_delta: -1 },
  ],
};

describe('buildOperationsView', () => {
  it('maps the backend sla_statuses / error_budgets / red_line_gates payload without inventing values', () => {
    const view = buildOperationsView({ type: 'OPERATIONS_SLO', data: backendPayload });
    expect(view.source).toBe('live');

    const product = view.cards.find((c) => c.id === 'client_transactions')!;
    expect(product.status).toBe('BREACHED');
    expect(product.primary).toBe('99.98%');
    expect(product.budgetRemainingPct).toBeNull();
    expect(product.details).toEqual(
      expect.arrayContaining([
        { label: 'SLA', value: '300s' },
        { label: 'Last ingest', value: expect.stringContaining('10-12 05:55') },
      ]),
    );

    const budget = view.cards.find((c) => c.id === 'SLO-1')!;
    expect(budget.budgetRemainingPct).toBeCloseTo(75.8, 5);
    expect(budget.status).toBe('HEALTHY');

    expect(view.gates).toEqual([
      { id: 'RL-1', name: 'Metric Calculation Determinism', status: 'PASS' },
      { id: 'RL-2', name: 'Four-Eyes Enforcement Integrity', status: 'FAIL' },
    ]);
  });

  it('summarises a breach honestly instead of claiming everything is healthy', () => {
    const view = buildOperationsView({ type: 'OPERATIONS_SLO', data: backendPayload });
    expect(view.summary.tone).toBe('bad');
    expect(view.summary.label).toBe('1 OF 3 BREACHED');
    expect(view.gateSummary).toEqual({ tone: 'bad', label: '1/2 PASSING' });
  });

  it('reports ALL HEALTHY only when every card is healthy', () => {
    const healthy = {
      ...backendPayload,
      sla_statuses: backendPayload.sla_statuses.map((s) => ({ ...s, status: 'HEALTHY' })),
    };
    const view = buildOperationsView({ type: 'OPERATIONS_SLO', data: healthy });
    expect(view.summary).toEqual({ tone: 'ok', label: 'ALL 3 HEALTHY' });
  });

  it('reports DEGRADED when nothing is breached but something is degraded', () => {
    const degraded = {
      ...backendPayload,
      sla_statuses: backendPayload.sla_statuses.map((s, i) => ({ ...s, status: i === 0 ? 'DEGRADED' : 'HEALTHY' })),
    };
    const view = buildOperationsView({ type: 'OPERATIONS_SLO', data: degraded });
    expect(view.summary).toEqual({ tone: 'warn', label: '1 OF 3 DEGRADED' });
  });

  it('accepts the fixture shape (array of SloHealthItem) as live data', () => {
    const view = buildOperationsView({
      type: 'OPERATIONS_SLO',
      data: [
        { sloId: 'SLO-1', name: 'Lag', targetValue: '< 30s', currentValue: '18.4s', status: 'HEALTHY', errorBudgetRemainingPct: 75.8, freshnessLatencySec: 18.4, dlqQuarantineDepth: 0 },
      ],
    });
    expect(view.source).toBe('live');
    expect(view.cards[0]).toMatchObject({ id: 'SLO-1', primary: '18.4s', budgetRemainingPct: 75.8, status: 'HEALTHY' });
  });

  it('falls back to a clearly flagged illustrative baseline when there is no usable payload', () => {
    for (const bad of [null, undefined, {}, { type: 'CHURN_RADAR', data: [] }, { type: 'OPERATIONS_SLO', data: 'nope' }]) {
      const view = buildOperationsView(bad);
      expect(view.source).toBe('baseline');
      expect(view.cards).toHaveLength(6);
      expect(view.gates).toHaveLength(7);
    }
  });

  it('treats an unknown gate status or card status conservatively', () => {
    const view = buildOperationsView({
      type: 'OPERATIONS_SLO',
      data: {
        sla_statuses: [{ product_name: 'x', status: 'WEIRD', freshness_sla_seconds: 1, null_check_pass_rate: 1, last_ingestion_timestamp: '2026-10-12T00:00:00Z' }],
        red_line_gates: [{ gate_id: 'RL-9', name: 'g', status: 'MAYBE' }],
      },
    });
    expect(view.cards[0].status).toBe('DEGRADED');
    expect(view.gates[0].status).toBe('FAIL');
  });
});
