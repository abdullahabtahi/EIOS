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

export interface Jurisdiction {
  readonly code: string;
  readonly name: string;
  readonly position: LngLat;
  readonly riskTier: RiskTier;
  readonly volumeUsd: number;
}

export interface Corridor {
  readonly id: string;
  readonly origin: string;
  readonly destination: string;
  readonly volumeUsd: number;
  readonly riskTier: RiskTier;
  readonly accountCount: number;
}

export interface Mismatch {
  readonly accountId: string;
  readonly kycCountry: string;
  readonly ipCountry: string;
  readonly volumeUsd: number;
}

export interface GeoEvidence {
  readonly source: string;
  readonly asOf: string;
  readonly jurisdictions: readonly Jurisdiction[];
  readonly corridors: readonly Corridor[];
  readonly mismatches: readonly Mismatch[];
}

export type GeoSelection =
  | { readonly kind: 'country'; readonly id: string }
  | { readonly kind: 'corridor'; readonly id: string }
  | { readonly kind: 'mismatch'; readonly id: string }
  | null;

export interface GeoSummary {
  /** null when no corridor was measured: never zero, never healthy. */
  readonly corridorVolumeUsd: number | null;
  readonly volumeByTier: Readonly<Record<RiskTier, number>>;
  readonly topCorridors: readonly Corridor[];
  readonly mismatchCount: number;
}
