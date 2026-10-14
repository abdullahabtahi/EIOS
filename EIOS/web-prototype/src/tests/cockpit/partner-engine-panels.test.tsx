import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { CockpitProvider, useCockpit } from '@/components/cockpit/state/cockpit-context';
import { PartnerWorkstationView } from '@/components/cockpit/workstations/partner-workstation';
import { PartnerOntologyInspector } from '@/components/cockpit/workstations/partner-ontology-inspector';
import { getMockWorkstationState } from '@/components/cockpit/state/fixtures';
import { toPartnerItem } from '@/components/cockpit/state/partner-radar';
import type { WorkstationApiResponse } from '@/components/cockpit/state/cockpit-types';

const partner = {
  partner_id: 'PTR-882',
  name: 'Alpha FX LatAm Master',
  tier: 'TIER_1_SUPER',
  realized_volume_30d_usd: 236236.71,
  churn_hazard_probability: 0.9491,
  quadrant: 'HIGH_VALUE_HIGH_RISK',
  days_to_intervention_deadline: 7,
  primary_root_cause: "Payout delays on referred clients' withdrawals",
  login_decay_pct: -43.6,
  ftd_decay_pct: -23.5,
  region: 'LatAm (Colombia)',
  cohort: 'LatAm P2P Cashier',
  historical_drift: { tMinus30d: { pChurn: 0.4, valueAtRiskUsd: 114868 }, tMinus14d: { pChurn: 0.22, valueAtRiskUsd: 65216 }, driftVelocityPct: 136.1 },
  empirical_win_rate: null,
  primary_driver: 'OPERATIONAL_CASHIER',
  support_ticket_count: 4,
  cashier_latency_sla_hours: 7.79,
  mirror_trade_correlation: 0.8878,
  extracted_commission_usd: 130,
};
const other = { ...partner, partner_id: 'PTR-6737', name: 'Ghana Apex Signals Group', churn_hazard_probability: 0.2, mirror_trade_correlation: 0, competitor_poaching: undefined };

const tree = {
  master_partner_id: 'PTR-882',
  name: 'Alpha FX LatAm Master',
  active_sub_affiliates_count: 12,
  referred_client_count: 19,
  sub_affiliates: [{ id: 'PTR-1606', name: 'Brazil Crest Affiliates', volume_usd: 179263, churn_hazard_probability: 0.198, co_occurrence_pct: 88.8, flagged_mirror_trading: true }],
  detected_abusive_rings: [
    { ring_id: 'PAIR-1', scheme: 'Opposite trading on Boom 1000', paired_accounts: ['CR748103', 'CR763977'], partners: ['PTR-1606', 'PTR-1000'], matched_timing_seconds: 2.61, unearned_commission_liability_usd: 130, co_occurrences: 13, collusion_confidence: 0.8878 },
  ],
  aml_exposure: [],
  statement: 'Observed patterns only; they are not a finding about the partner\'s intent.',
};

const cohortStage = { action_type: 'LaunchRetentionPlaybook', target_entity_id: 'ALERT-COHORT-SEA-20261014', severity: 'MEDIUM', requires_four_eyes: true, metadata: { partner_ids: ['PTR-723'], playbook_id: 'pb_regional_incentive', budget: 9870 } };

const engineWorkstation = (): WorkstationApiResponse => ({
  ...getMockWorkstationState('partner_manager'),
  dataOrigin: 'engine',
  activeDossier: { ...getMockWorkstationState('partner_manager').activeDossier, entityId: 'PTR-882', tradeOffs: [] },
  canvasPayload: { type: 'CHURN_RADAR', data: { partners: [partner, other], affiliate_tree: tree } } as WorkstationApiResponse['canvasPayload'],
});

const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });

function Open() {
  const { setRole } = useCockpit();
  return <button type="button" data-testid="go" onClick={() => setRole('partner_manager')} />;
}

describe('toPartnerItem', () => {
  it('maps computed fields and leaves what was not computed undefined', () => {
    const item = toPartnerItem({ partner_id: 'PTR-1', churn_hazard_probability: 0.3, realized_volume_30d_usd: 10 });
    expect(item.mirrorTradeCorrelation).toBeUndefined();
    expect(item.competitorPoaching).toBeUndefined();
    expect(item.projectedLiftPct).toBeUndefined();
    expect(item.empiricalPlaybookWinRate).toBeUndefined();
    expect(toPartnerItem(partner).cashierLatencyHours).toBe(7.79);
  });
});

describe('Engine-backed partner workstation', () => {
  let calls: Array<{ url: string; body?: string }>;

  beforeEach(() => {
    calls = [];
    global.fetch = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      calls.push({ url, body: init?.body as string | undefined });
      if (url.includes('/actions/stage')) {
        return ok({ status: 'STAGED', card: { intent_id: 'intent-9', action_type: JSON.parse(String(init?.body)).action_type, target_entity_id: 'x', lifecycle_state: 'STAGED', kms_signature: { key_id: 'k', algorithm: 'ECDSA_P256_SHA256', signature_digest: 'd', verified: true } } });
      }
      if (url.includes('/churn/cohorts')) {
        return ok({ cohorts: [{ cohort_id: 'ALERT-COHORT-SEA-20261014', region: 'SEA', partner_count: 31, aggregate_value_at_risk_usd: 4303321.99, p_value: 0.006563, primary_driver: 'Synchronized disengagement', affected_partner_ids: ['PTR-723'], stage_request: cohortStage }] });
      }
      if (url.includes('/churn/radar')) return ok({ partners: [partner, other] });
      if (url.includes('/ontology')) return Promise.resolve({ ok: false, status: 503, json: () => Promise.resolve({}) });
      return ok(engineWorkstation());
    }) as unknown as typeof fetch;
  });
  afterEach(() => vi.restoreAllMocks());

  const mount = async (ui: React.ReactNode) => {
    render(
      <CockpitProvider>
        <Open />
        {ui}
      </CockpitProvider>,
    );
    await act(async () => {
      screen.getByTestId('go').click();
    });
  };

  it('lists the computed partners and none of the samples', async () => {
    await mount(<PartnerWorkstationView />);
    await waitFor(() => expect(screen.getByTestId('triage-row-PTR-6737')).toBeInTheDocument());
    expect(screen.queryByTestId('triage-row-PTR-104')).not.toBeInTheDocument();
    expect(screen.queryByText(/Bancolombia|Exness|11\/14|Brier|Carlos Mendez/)).not.toBeInTheDocument();
  });

  it('shows the inspector from computed fields and says when no outcomes exist', async () => {
    await mount(<PartnerWorkstationView />);
    await waitFor(() => expect(screen.getAllByText('7.8 h')[0]).toBeInTheDocument());
    expect(screen.getByText(/no playbook outcomes recorded yet/)).toBeInTheDocument();
    expect(screen.getByText('89% confidence')).toBeInTheDocument();
  });

  it('stages the cohort playbook the backend priced, through the intent hub', async () => {
    await mount(<PartnerWorkstationView />);
    fireEvent.click(screen.getByRole('button', { name: /^COHORTS/i }));
    const stage = await screen.findByRole('button', { name: /Stage a retention playbook for the SEA cohort/ });
    expect(screen.getByText(/31 partners at high risk together/)).toBeInTheDocument();
    fireEvent.click(stage);
    await waitFor(() => expect(calls.some((c) => c.url.includes('/actions/stage'))).toBe(true));
    const sent = calls.find((c) => c.url.includes('/actions/stage'));
    expect(JSON.parse(sent?.body ?? '{}')).toEqual(cohortStage);
  });

  it('renders the referral network with the detected pair and stages a clawback through the hub', async () => {
    await mount(<PartnerWorkstationView />);
    await waitFor(() => expect(screen.getByText('Opposite trading on Boom 1000')).toBeInTheDocument());
    expect(screen.getByText(/19 referred clients/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Stage commission clawback/ }));
    await waitFor(() => expect(calls.some((c) => c.url.includes('/actions/stage'))).toBe(true));
    const sent = JSON.parse(calls.find((c) => c.url.includes('/actions/stage'))?.body ?? '{}');
    expect(sent.action_type).toBe('ClawbackCommission');
    expect(sent.metadata).toMatchObject({ partner_id: 'PTR-1606', amount: 130 });
  });

  it('says the partner object could not be loaded instead of showing a sample', async () => {
    await mount(<PartnerOntologyInspector />);
    await act(async () => undefined);
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded');
  });
});
