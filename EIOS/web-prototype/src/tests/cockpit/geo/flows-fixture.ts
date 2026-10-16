import type { GeoFlows } from '@/components/cockpit/geo/geo-types';

/** A tiny stand-in for the real flows payload; shapes match `/api/cockpit/geo/flows`. Countries are in reference-fixture. */
export const FLOWS: GeoFlows = {
  source: 'AML engine over the seeded world',
  as_of: '2026-10-14T08:00:00+00:00',
  tiers_known: true,
  corridors: [
    { origin: 'NO', destination: 'IR', volume_usd: 900_000, accounts: 4, events: 12, tier: 'high', sample_accounts: ['CR84920', 'CR33333'], deposits: 9, withdrawals: 3 },
    { origin: 'KE', destination: 'BS', volume_usd: 400_000, accounts: 9, events: 30, tier: 'medium' },
    { origin: 'PA', destination: 'NO', volume_usd: 100_000, accounts: 20, events: 55, tier: 'low' },
  ],
  mismatch_pairs: [
    { kyc_country: 'NO', ip_country: 'KE', accounts: 23, events: 90, foreign_events: 80, volume_usd: 700_000, sample_accounts: ['CR84920', 'CR11111'] },
    { kyc_country: 'PA', ip_country: 'BS', accounts: 2, events: 8, foreign_events: 7, volume_usd: 20_000, sample_accounts: ['CR22222'] },
  ],
  exposure: { low: 100_000, medium: 400_000, high: 900_000 },
};
