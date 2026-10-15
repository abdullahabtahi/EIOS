import type { GeoAccount, GeoGateway } from '@/components/cockpit/geo/geo-types';

/** Shapes match `/api/cockpit/geo/flows` gateways and `/api/cockpit/geo/accounts/{id}`. */
export const GATEWAY: GeoGateway = {
  gateway_id: 'GW-KE-X00',
  country: 'KE',
  accounts: 3,
  home_countries: [
    { iso2: 'NO', accounts: 2 },
    { iso2: 'PA', accounts: 1 },
  ],
  impossible_jumps: 7,
  sample_accounts: ['CR84920', 'CR11111', 'CR22222'],
};

export const ACCOUNT: GeoAccount = {
  account_id: 'CR84920',
  kyc_country: 'NO',
  source: 'AML engine over the seeded world (login sessions, gateways, payments)',
  as_of: '2026-10-14T08:00:00+00:00',
  sessions: 12,
  login_countries: [
    { iso2: 'KE', sessions: 9 },
    { iso2: 'NO', sessions: 3 },
  ],
  gateways: [
    { gateway_id: 'GW-KE-X00', country: 'KE', sessions: 9, accounts: 3, hub: false, shared_exit: true },
    { gateway_id: 'GW-NO-R12', country: 'NO', sessions: 3, accounts: 1, hub: false, shared_exit: false },
  ],
  jumps: { count: 2, via_hub: 0, examples: [{ from: 'NO', to: 'KE', hours: 2.5, km: 7120, at: '2026-10-01T10:00:00+00:00' }] },
  payments: [{ iso2: 'IR', direction: 'out', events: 2, volume_usd: 4000, tier: 'high' }],
  lenses: {
    mismatch: { flag: true, assessable: true, foreign_events: 9, events: 12 },
    shared_exit: { flag: true, gateway: 'GW-KE-X00', sessions: 9 },
    travel: { flag: true, assessable: true },
    corridor: { flag: false, assessable: true },
  },
  geo_score: 2.5,
  neighbourhood: {
    source: 'graph.bigquery:p.warm_graph.aml_geo',
    seconds: 1.8,
    total: 3,
    rows: [
      { via: 'gateway', link: 'GW-KE-X00', detail: 'KE', account_id: 'CR11111', kyc_country: 'NO' },
      { via: 'gateway', link: 'GW-KE-X00', detail: 'KE', account_id: 'CR22222', kyc_country: 'PA' },
      { via: 'identifier', link: 'tok_dev_1', detail: 'DEVICE_FINGERPRINT', account_id: 'CR11111', kyc_country: 'NO' },
    ],
    error: null,
  },
};
