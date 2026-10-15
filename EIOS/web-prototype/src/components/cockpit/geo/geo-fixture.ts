import type { GeoEvidence } from './geo-types';

/**
 * [ILLUSTRATIVE] Scaffold fixture, not engine output. Centroids are approximate country centres
 * [ASSUMPTION]; risk tiers are a demo tiering, not a published list [ASSUMPTION]. It is replaced by the
 * engine-backed `/api/aml/geo` read model once the foundry plants geo anomalies.
 */
export const GEO_FIXTURE: GeoEvidence = {
  source: 'Scaffold fixture (not engine data)',
  asOf: '2026-10-10T10:00:00Z',
  jurisdictions: [
    { code: 'GB', name: 'United Kingdom', position: [-1.5, 53.0], riskTier: 'low', volumeUsd: 4_200_000 },
    { code: 'AE', name: 'United Arab Emirates', position: [54.4, 24.3], riskTier: 'medium', volumeUsd: 3_100_000 },
    { code: 'SG', name: 'Singapore', position: [103.8, 1.35], riskTier: 'low', volumeUsd: 2_600_000 },
    { code: 'HK', name: 'Hong Kong', position: [114.17, 22.32], riskTier: 'medium', volumeUsd: 2_200_000 },
    { code: 'CY', name: 'Cyprus', position: [33.2, 35.0], riskTier: 'medium', volumeUsd: 1_700_000 },
    { code: 'MT', name: 'Malta', position: [14.4, 35.9], riskTier: 'medium', volumeUsd: 900_000 },
    { code: 'MU', name: 'Mauritius', position: [57.6, -20.3], riskTier: 'high', volumeUsd: 1_300_000 },
    { code: 'PA', name: 'Panama', position: [-80.1, 8.5], riskTier: 'high', volumeUsd: 1_100_000 },
    { code: 'KY', name: 'Cayman Islands', position: [-81.25, 19.3], riskTier: 'high', volumeUsd: 800_000 },
    { code: 'ZA', name: 'South Africa', position: [24.7, -29.0], riskTier: 'medium', volumeUsd: 700_000 },
    { code: 'NG', name: 'Nigeria', position: [8.7, 9.1], riskTier: 'high', volumeUsd: 1_000_000 },
    { code: 'BR', name: 'Brazil', position: [-51.9, -14.2], riskTier: 'medium', volumeUsd: 1_400_000 },
  ],
  corridors: [
    { id: 'C-GB-AE', origin: 'GB', destination: 'AE', volumeUsd: 1_400_000, riskTier: 'medium', accountCount: 41 },
    { id: 'C-AE-MU', origin: 'AE', destination: 'MU', volumeUsd: 920_000, riskTier: 'high', accountCount: 17 },
    { id: 'C-SG-HK', origin: 'SG', destination: 'HK', volumeUsd: 880_000, riskTier: 'low', accountCount: 33 },
    { id: 'C-CY-PA', origin: 'CY', destination: 'PA', volumeUsd: 640_000, riskTier: 'high', accountCount: 9 },
    { id: 'C-GB-CY', origin: 'GB', destination: 'CY', volumeUsd: 610_000, riskTier: 'medium', accountCount: 22 },
    { id: 'C-BR-KY', origin: 'BR', destination: 'KY', volumeUsd: 540_000, riskTier: 'high', accountCount: 12 },
    { id: 'C-NG-AE', origin: 'NG', destination: 'AE', volumeUsd: 480_000, riskTier: 'high', accountCount: 14 },
    { id: 'C-MT-GB', origin: 'MT', destination: 'GB', volumeUsd: 350_000, riskTier: 'medium', accountCount: 11 },
    { id: 'C-ZA-MU', origin: 'ZA', destination: 'MU', volumeUsd: 300_000, riskTier: 'medium', accountCount: 8 },
    { id: 'C-HK-SG', origin: 'HK', destination: 'SG', volumeUsd: 260_000, riskTier: 'low', accountCount: 19 },
  ],
  mismatches: [
    { accountId: 'CR84920', kycCountry: 'GB', ipCountry: 'NG', volumeUsd: 184_000 },
    { accountId: 'CR51377', kycCountry: 'SG', ipCountry: 'AE', volumeUsd: 96_000 },
    { accountId: 'CR20468', kycCountry: 'BR', ipCountry: 'PA', volumeUsd: 143_000 },
    { accountId: 'CR77013', kycCountry: 'ZA', ipCountry: 'MU', volumeUsd: 61_000 },
    { accountId: 'CR39952', kycCountry: 'MT', ipCountry: 'CY', volumeUsd: 38_000 },
  ],
};
