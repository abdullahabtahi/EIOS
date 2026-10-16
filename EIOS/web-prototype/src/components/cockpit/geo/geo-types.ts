/**
 * Evidence model for the geospatial lens. Entity and jurisdiction level only (policy P-2): a mark is a
 * country, a corridor between two countries, or an account's KYC-versus-IP country pair. Every payload
 * states its source and as-of, so nothing is drawn without a stated origin.
 */

export type RiskTier = 'low' | 'medium' | 'high';

export type LayerId = 'risk' | 'offshore' | 'corridors' | 'mismatches';

export type FatfList = 'call_for_action' | 'increased_monitoring';

export type BaselBand = 'higher' | 'medium' | 'lower';

/** A country's Basel AML Index score (0 lowest risk to 10) with its place among the rated countries. */
export interface BaselScore {
  readonly score: number;
  readonly rank: number;
  readonly of: number;
  readonly band: BaselBand;
}

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
  readonly eu_high_risk: boolean;
  /** null: not in the Public Edition, so unrated (never low). */
  readonly basel: BaselScore | null;
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
  readonly sources: Readonly<Record<'boundaries' | 'fatf' | 'eu_list' | 'basel_aml' | 'offshore_precedent' | 'indicators', ReferenceSource>>;
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
  /** Gateways abroad shared by accounts that live elsewhere (hubs above the RL-4 line excluded). */
  readonly gateways?: readonly GeoGateway[];
  /** Gateways shared so widely they were suppressed as hubs (RL-4); null when the world has no sessions. */
  readonly hubs_suppressed?: number | null;
}

export interface GeoGateway {
  readonly gateway_id: string;
  readonly country: string;
  readonly accounts: number;
  readonly home_countries: readonly { readonly iso2: string; readonly accounts: number }[];
  readonly impossible_jumps: number;
  readonly sample_accounts: readonly string[];
}

/** One account's geography as case evidence (`/api/cockpit/geo/accounts/{id}`). */
export interface GeoAccount {
  readonly account_id: string;
  readonly kyc_country: string;
  readonly source: string;
  readonly as_of: string;
  readonly sessions: number;
  readonly login_countries: readonly { readonly iso2: string; readonly sessions: number }[];
  readonly gateways: readonly {
    readonly gateway_id: string;
    readonly country: string;
    readonly sessions: number;
    readonly accounts: number | null;
    readonly hub: boolean | null;
    readonly shared_exit: boolean | null;
  }[];
  /** null when the travel lens could not be assessed (no country positions): not the same as no jumps. */
  readonly jumps: {
    readonly count: number;
    readonly via_hub: number;
    readonly examples: readonly { readonly from: string; readonly to: string; readonly hours: number; readonly km: number; readonly at: string }[];
  } | null;
  readonly payments: readonly { readonly iso2: string; readonly direction: 'in' | 'out'; readonly events: number; readonly volume_usd: number; readonly tier: RiskTier | null }[];
  readonly lenses: {
    readonly mismatch: { readonly flag: boolean; readonly assessable: boolean; readonly foreign_events: number; readonly events: number };
    readonly shared_exit: { readonly flag: boolean; readonly gateway: string | null; readonly sessions: number };
    readonly travel: { readonly flag: boolean; readonly assessable: boolean };
    readonly corridor: { readonly flag: boolean; readonly assessable: boolean };
  };
  readonly geo_score: number;
  readonly neighbourhood: {
    readonly source: string | null;
    readonly seconds?: number;
    readonly total?: number;
    readonly rows: readonly { readonly via: 'gateway' | 'identifier'; readonly link: string; readonly detail: string; readonly account_id: string; readonly kyc_country: string }[] | null;
    readonly error: string | null;
  };
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

/** What the network reference says about one IP address (`POST /api/cockpit/geo/address`). */
export type AddressVerdict = 'tor_exit' | 'vpn' | 'cloud' | 'datacenter' | 'none_listed' | 'not_public';
export type AddressListName = 'tor_exit' | 'vpn' | 'cloud' | 'datacenter';

export interface GeoAddress {
  readonly address: string;
  readonly version: 4 | 6;
  /** `public`, or why the address is not looked up (private, loopback, link_local, multicast, unspecified, reserved). */
  readonly scope: string;
  /** null: the database does not know this address. Where it is registered, not where its user is. */
  readonly country: { readonly iso2: string; readonly name: string } | null;
  readonly network: { readonly asn: number; readonly name: string; readonly domain: string } | null;
  readonly verdict: AddressVerdict;
  readonly lists: readonly { readonly list: AddressListName; readonly detail: string }[];
  /** Lists that hold no network of this address family: they cannot rule it out. */
  readonly uncovered: readonly AddressListName[];
  readonly sources: readonly { readonly name: string; readonly as_of: string }[];
}

/** The two published lists whose latest change the book can be compared against. */
export type ListId = 'fatf' | 'eu';

/** One country a list change names, with what this book does there (`/api/cockpit/geo/list-changes`). */
export interface ListChangeCountry {
  readonly iso2: string;
  readonly name: string;
  readonly before: string | null;
  readonly after: string | null;
  readonly registered_accounts: number;
  /** null: no login sessions on this plane, not zero logins. */
  readonly login_accounts: number | null;
  readonly sessions: number | null;
  readonly payment_accounts: number;
  readonly payment_volume_usd: number;
  readonly shared_exits: readonly string[] | null;
  readonly exposed_accounts: number;
  /** Accounts one shared device, payment token or address away (BigQuery Graph); null when the graph could not answer. */
  readonly linked_accounts: number | null;
}

export interface ListChangeGroup {
  readonly countries: readonly ListChangeCountry[];
  readonly exposed_accounts: number;
  readonly sessions: number;
  readonly payment_volume_usd: number;
  /** Each country's share of the group's sessions or payments, summing to 100.0; null when there is nothing to share. */
  readonly session_shares: Readonly<Record<string, number>> | null;
  readonly payment_shares: Readonly<Record<string, number>> | null;
}

export interface ListEditionInfo {
  readonly label: string;
  readonly in_force: string;
  readonly source: string;
}

export interface GeoListChange {
  readonly list_id: ListId;
  readonly as_of: string;
  readonly source: string;
  readonly before: ListEditionInfo;
  readonly after: ListEditionInfo;
  readonly added: ListChangeGroup;
  readonly removed: ListChangeGroup;
  readonly relisted: ListChangeGroup;
  readonly graph: { readonly source: string | null; readonly seconds: number | null; readonly error: string | null };
}
