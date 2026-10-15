/**
 * Evidence model for the geospatial lens. Entity and jurisdiction level only (policy P-2): a mark is a
 * country, a corridor between two countries, or an account's KYC-versus-IP country pair. Every payload
 * states its source and as-of, so nothing is drawn without a stated origin.
 */

export type RiskTier = 'low' | 'medium' | 'high';

export type LayerId = 'risk' | 'offshore' | 'corridors' | 'mismatches';

export type FatfList = 'call_for_action' | 'increased_monitoring';

/** Reference layer: real public data from `warm_reference`, one row per country or dependency. */
export interface ReferenceIndicator {
  readonly code: string;
  readonly name: string;
  readonly year: number;
  readonly value: number;
}

export interface ReferenceCountry {
  readonly iso2: string;
  readonly name: string;
  /** GeoJSON Polygon or MultiPolygon, simplified for display. */
  readonly boundary: { readonly type: string; readonly coordinates: unknown };
  readonly position: LngLat;
  readonly fatf_list: FatfList | null;
  /** null means nothing was measured for this country, never zero. */
  readonly entities_incorporated: number | null;
  readonly entities_linked: number | null;
  readonly indicators: readonly ReferenceIndicator[];
}

export interface ReferenceSource {
  readonly source: string;
  readonly as_of: string | null;
}

export interface GeoReference {
  readonly countries: readonly ReferenceCountry[];
  readonly sources: Readonly<Record<'boundaries' | 'fatf' | 'offshore_precedent' | 'indicators', ReferenceSource>>;
}

/** [longitude, latitude] */
export type LngLat = readonly [number, number];

/** Customer flows from the geo engine (`/api/cockpit/geo/flows`). Countries are placed using the reference layer. */
export interface FlowCorridor {
  readonly origin: string;
  readonly destination: string;
  readonly volume_usd: number;
  readonly accounts: number;
  readonly events: number;
  /** null when jurisdiction tiers are unknown: never "low". */
  readonly tier: RiskTier | null;
}

export interface MismatchPair {
  readonly kyc_country: string;
  readonly ip_country: string;
  readonly accounts: number;
  readonly events: number;
  readonly foreign_events: number;
  readonly volume_usd: number;
  readonly sample_accounts: readonly string[];
}

export interface GeoFlows {
  readonly source: string;
  readonly as_of: string;
  readonly tiers_known: boolean;
  readonly corridors: readonly FlowCorridor[];
  readonly mismatch_pairs: readonly MismatchPair[];
  /** Corridor volume by tier; null when tiers are unknown. */
  readonly exposure: Readonly<Record<RiskTier, number>> | null;
  /** How many clients each lens can judge at all; the rest have too few events and are not assessable, never clean. */
  readonly coverage?: GeoCoverage;
}

export interface GeoCoverage {
  readonly clients: number;
  readonly mismatch_assessable: number;
  readonly corridor_assessable: number | null;
}

export type GeoSelection =
  | { readonly kind: 'country'; readonly id: string }
  | { readonly kind: 'corridor'; readonly id: string } // `${origin}>${destination}`
  | { readonly kind: 'mismatch'; readonly id: string } // `${kyc_country}>${ip_country}`
  | { readonly kind: 'gateway'; readonly id: string } // a login gateway (egress) id
  | { readonly kind: 'account'; readonly id: string } // a client id
  | null;

export interface GeoSummary {
  /** null when no corridor was measured: never zero, never healthy. */
  readonly corridorVolumeUsd: number | null;
  readonly exposure: Readonly<Record<RiskTier, number>> | null;
  readonly flaggedAccounts: number;
}
