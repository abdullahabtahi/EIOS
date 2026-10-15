import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider } from '@/components/cockpit/state/cockpit-context';
import { ExecutiveCockpitView } from '@/components/cockpit/workstations/executive-cockpit';

const provenance = {
  metric_id: 'net_revenue_usd',
  definition_version: '1.4.0',
  as_of_timestamp: '2026-10-14T08:00:00+00:00',
  computation_source: 'ExecutiveEngine.Series',
  owner_role: 'Chief Financial Officer',
};
const horizon = (horizon_name: string, headline: string, observed_value: number) => ({
  horizon_name,
  headline,
  primary_metric_id: 'net_revenue_usd',
  observed_value,
  delta_period_pct: -0.9,
  provenance,
});

const board = {
  data_origin: 'engine',
  as_of: '2026-10-14T08:00:00+00:00',
  briefing: {
    horizons: [
      horizon('Competitive', 'Competitor payout rate is 0.567, +2.7% over 28 days.', 0.567),
      horizon('Partner', '70 partners are above a 50% 30-day churn hazard.', 8381260),
      horizon('Client', '50 priority AML cases cover 116 accounts.', 738770),
      horizon('Financial', 'Net revenue is projected at $4,301,020 in 28 days.', 4301020),
    ],
    risks: [{ risk_id: 'rsk_partner_PTR-1', title: 'Alpha FX (PTR-1) is likely to disengage', severity: 'HIGH', exposure_usd: 548449 }],
    opportunities: [
      { opportunity_id: 'opp_pb_x_PTR-1', title: 'Reconcile the rebate for Alpha FX', projected_upside_usd: 4965, recommended_action_type: 'DeployRetentionConcession' },
    ],
  },
  figures: { Competitive: '0.567', Partner: '$8,381,261', Client: '$738,770', Financial: '$4,301,020' },
  forecast: {
    point_estimate: 4301019.8,
    delta_period_pct: -0.86,
    interval_low: 4075619,
    interval_high: 4637748,
    interval_nominal: 0.9,
    interval_coverage: 0.87,
    skill_vs_persistence: 0.743,
    backtest_origins: 75,
    horizon_days: 28,
    assumption: 'competitor payout rate decays toward its mean',
  },
  dag: {
    nodes: [
      { node_id: 'competitor_payout_rate', label: 'Competitor Payout Rate', domain: 'Competitive', current_value: 0.567 },
      { node_id: 'avg_spread_pip', label: 'Average Spread (pips)', domain: 'Competitive', current_value: 1.6 },
      { node_id: 'partner_churn_rate', label: 'Partner Churn Rate', domain: 'Partner', current_value: 0.22 },
    ],
    edges: [
      { source_node_id: 'competitor_payout_rate', target_node_id: 'partner_churn_rate', weight: 0.886, refuter: { confidence: 0.99, placebo_p_value: 0.6, is_causal_verified: true, status_label: 'Verified Causal' } },
      { source_node_id: 'avg_spread_pip', target_node_id: 'partner_churn_rate', weight: -0.0005, refuter: { confidence: 0, placebo_p_value: 0.37, is_causal_verified: false, status_label: 'Correlation Detected; Insufficient Evidence' } },
    ],
  },
  shocks: [{ id: 'competitor_payout_increase', label: 'Competitor raises its payout', driver: 'Competitor payout rate, % change' }],
  stage_requests: {
    'opp_pb_x_PTR-1': { action_type: 'DeployRetentionConcession', target_entity_id: 'PTR-1', severity: 'MEDIUM', requires_four_eyes: false, metadata: { partner_ids: ['PTR-1'] } },
  },
};

const simulation = (revenue: number, extra: Record<string, unknown> = {}) => ({
  shock_param: 'competitor_payout_increase',
  magnitude_pct: 10,
  latency_ms: 0.4,
  projected_changes: { partner_churn_delta_pct: 5.03, first_deposit_delta_pct: -9.1, projected_revenue_impact_usd: revenue },
  attribution_waterfall: [
    { driver: 'SEA partners', contribution_pct: 60.5 },
    { driver: 'EU partners', contribution_pct: 39.5 },
  ],
  attribution_sum_pct: 100,
  confidence_interval: [revenue * 1.1, revenue * 0.9],
  mitigations: [{ playbook_id: 'pb_a', title: 'Whitelist a direct cashier rail', action_type: 'WhitelistDirectCashierRail', target_region: 'SEA', partners: 4, estimated_cost_usd: 0, projected_margin_kept_usd: 5454 }],
  mitigation_basis: 'Model projection under the hazard model; not a causal estimate',
  extrapolates_beyond_history: false,
  causal_label: 'VERIFIED_CAUSAL',
  causal_reason: 'every link on the shock path passed the placebo refuter',
  ...extra,
});

const json = (status: number, body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status }));

function stub(handler: (url: string, init?: RequestInit) => Promise<Response>) {
  global.fetch = vi.fn().mockImplementation(handler) as unknown as typeof fetch;
}

function view() {
  return render(
    <CockpitProvider>
      <ExecutiveCockpitView />
    </CockpitProvider>,
  );
}

describe('Executive Decision Cockpit (spec 034)', () => {
  const original = global.fetch;
  beforeEach(() => vi.useRealTimers());
  afterEach(() => {
    global.fetch = original;
  });

  it('shows the four horizons, the measured projection and the causal verdicts from the backend board', async () => {
    stub((url) => (url.includes('/api/cockpit/executive') ? json(200, board) : json(404, {})));
    view();
    expect(await screen.findByText(/Competitor payout rate is 0.567/)).toBeInTheDocument();
    for (const name of ['COMPETITIVE', 'PARTNER FLOW', 'CLIENT RETENTION', 'FINANCIAL METRICS']) {
      expect(screen.getAllByText(name)[0]).toBeInTheDocument();
    }
    expect(screen.getByText(/0\.74× the error of carrying/)).toBeInTheDocument();
    expect(screen.getByText(/interval held 87%/)).toBeInTheDocument();
    expect(screen.getByText('Verified Causal')).toBeInTheDocument();
    expect(screen.getByText('Correlation Detected; Insufficient Evidence')).toBeInTheDocument();
    expect(screen.queryByText(/18 bps/)).not.toBeInTheDocument();
  });

  it('asks the engine on every slider move and shows its effect, closure and defences', async () => {
    stub((url, init) => {
      if (url.includes('/api/cockpit/executive')) return json(200, board);
      const m = JSON.parse(String(init?.body)).magnitude_pct as number;
      return json(200, simulation(m * -33754));
    });
    view();
    const slider = await screen.findByLabelText(/What-if shock slider/i);
    fireEvent.change(slider, { target: { value: '25' } });
    expect(await screen.findByText('-$843,850')).toBeInTheDocument();
    expect(screen.getByText(/Σ Attribution = 100.0%/)).toBeInTheDocument();
    expect(screen.getByText('Verified')).toBeInTheDocument();
    expect(screen.getByText(/Whitelist a direct cashier rail/)).toBeInTheDocument();
    const posts = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.filter(([u]) => String(u).includes('simulate'));
    expect(JSON.parse(String(posts.at(-1)?.[1]?.body))).toEqual({ shock_param: 'competitor_payout_increase', magnitude_pct: 25 });
  });

  it('says so when a shock leaves the history, and relays a refusal without inventing a result', async () => {
    let refuse = false;
    stub((url) => {
      if (url.includes('/api/cockpit/executive')) return json(200, board);
      return refuse
        ? json(422, { detail: "'competitor_spread_cut' has no tested causal path to revenue" })
        : json(200, simulation(-3_375_432, { extrapolates_beyond_history: true, causal_label: 'CORRELATION_ONLY', causal_reason: 'outside the history' }));
    });
    view();
    const slider = await screen.findByLabelText(/What-if shock slider/i);
    fireEvent.change(slider, { target: { value: '50' } });
    expect(await screen.findByRole('status')).toHaveTextContent(/outside anything in the two-year history/);
    expect(screen.getAllByText('Correlation only').length).toBeGreaterThanOrEqual(2); // the legend and the verdict tile
    refuse = true;
    fireEvent.change(slider, { target: { value: '-5' } });
    expect(await screen.findByRole('alert')).toHaveTextContent(/no tested causal path/);
    expect(screen.queryByText('-$3,375,432')).not.toBeInTheDocument();
  });

  it('stages an opportunity through the intent hub with the backend-built request', async () => {
    const card = { intent_id: 'int_1', action_type: 'DeployRetentionConcession', target_entity_id: 'PTR-1', severity: 'MEDIUM', lifecycle_state: 'STAGED', requires_four_eyes: false };
    stub((url, init) => {
      if (url.includes('/api/cockpit/executive')) return json(200, board);
      if (url.includes('/actions/stage')) return json(200, { status: 'STAGED', card, total_staged: 1 });
      return json(200, simulation(-1));
    });
    view();
    fireEvent.click(await screen.findByRole('button', { name: /Stage through the intent hub/i }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Staged/i })).toBeDisabled());
    const call = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.find(([u]) => String(u).includes('/actions/stage'));
    expect(JSON.parse(String(call?.[1]?.body))).toEqual(board.stage_requests['opp_pb_x_PTR-1']);
  });

  it('shows a plain failure, not a stand-in, when the board cannot be read', async () => {
    stub(() => json(503, {}));
    view();
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not be loaded/);
    expect(screen.queryByText(/Morning Briefing/)).not.toBeInTheDocument();
  });
});
