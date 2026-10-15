import type { BaselBand, ReferenceCountry, RiskTier } from './geo-types';

/**
 * Which published list colours the Jurisdictions map. The three bases disagree on purpose: the EU follows the FATF with
 * a lag and adds entries of its own, and the Basel index scores countries the lists never name. Each is shown as
 * published, never blended into a score of ours.
 */
export type BasisId = 'fatf' | 'eu' | 'basel';

export const BASES: readonly { readonly id: BasisId; readonly label: string; readonly title: string }[] = [
  { id: 'fatf', label: 'FATF', title: 'FATF call-for-action and increased-monitoring lists' },
  { id: 'eu', label: 'EU', title: 'EU list of high-risk third countries' },
  { id: 'basel', label: 'Basel AML', title: 'Basel AML Index, Public Edition: risk score per country' },
];

export const DEFAULT_BASIS: BasisId = 'fatf';
export const isBasis = (value: string | null): value is BasisId => BASES.some((b) => b.id === value);

export const BAND_LABEL: Readonly<Record<BaselBand, string>> = { higher: 'Higher', medium: 'Medium', lower: 'Lower' };
/** The Institute's own breaks (Jenks): lower below 4.70, medium 4.70 to 6.08, higher above 6.08. */
export const BASEL_BREAKS = { medium: '4.70', higher: '6.08' } as const;

const BAND_TIER: Readonly<Record<BaselBand, RiskTier>> = { higher: 'high', medium: 'medium', lower: 'low' };

/** The tier a country draws in under a basis. Null is unrated and draws nothing: it is never low. */
export function areaTier(country: ReferenceCountry, basis: BasisId): RiskTier | null {
  if (basis === 'eu') return country.eu_high_risk ? 'medium' : null;
  if (basis === 'basel') return country.basel ? BAND_TIER[country.basel.band] : null;
  if (country.fatf_list === 'call_for_action') return 'high';
  return country.fatf_list === 'increased_monitoring' ? 'medium' : null;
}
