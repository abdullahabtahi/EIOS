import type { GeoListChange, RiskTier } from './geo-types';

/** The tier the map draws for a listing in a list change. Not listed, or a listing this build does not know, draws nothing: never low. */
export function listingTier(listing: string | null): RiskTier | null {
  if (listing === 'call_for_action') return 'high';
  if (listing === 'increased_monitoring' || listing === 'eu_high_risk') return 'medium';
  return null;
}

/** How many countries a change names: added, removed or moved between lists. */
export const changeCount = (change: GeoListChange): number =>
  change.added.countries.length + change.removed.countries.length + change.relisted.countries.length;

/**
 * The tier each changed country had under the earlier edition, for the map's "Before" side. Only the countries the change
 * names are in it; every other country keeps the colour it has today, because the change says nothing about it.
 */
export function beforeTiers(change: GeoListChange): ReadonlyMap<string, RiskTier | null> {
  const named = [...change.added.countries, ...change.removed.countries, ...change.relisted.countries];
  return new Map(named.map((c) => [c.iso2, listingTier(c.before)]));
}
