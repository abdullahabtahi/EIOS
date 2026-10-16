import type { SelectionView } from './geo-format';
import type { GeoListChange, ListChangeCountry, RiskTier } from './geo-types';

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

const LISTING: Readonly<Record<string, string>> = {
  call_for_action: 'call for action',
  increased_monitoring: 'increased monitoring',
  eu_high_risk: 'EU high-risk',
};
export const listingText = (listing: string | null): string => (listing ? (LISTING[listing] ?? listing) : 'not listed');

export type ChangeKind = 'added' | 'removed' | 'moved';

/** What happened to one country, in a line: the same words in the table, on the map's tooltip and on the country. */
export function describeChange(country: ListChangeCountry, kind: ChangeKind): string {
  if (kind === 'added') return `Added · ${listingText(country.after)}`;
  if (kind === 'removed') return `Removed · was ${listingText(country.before)}`;
  return `Moved · ${listingText(country.before)} → ${listingText(country.after)}`;
}

/** The line for each country a change names; a country it does not name has none. */
export function changeNotes(change: GeoListChange): ReadonlyMap<string, string> {
  const named: readonly (readonly [ListChangeCountry, ChangeKind])[] = [
    ...change.added.countries.map((c) => [c, 'added'] as const),
    ...change.removed.countries.map((c) => [c, 'removed'] as const),
    ...change.relisted.countries.map((c) => [c, 'moved'] as const),
  ];
  return new Map(named.map(([c, kind]) => [c.iso2, describeChange(c, kind)]));
}

/** A country description with its latest change as a last row, flagged so the card can offer the comparison; the original is left as it was. */
export function withChangeNote(view: SelectionView, note: string | undefined): SelectionView {
  if (!note) return view;
  return { ...view, rows: [...view.rows, ['Latest change', note] as const], changed: true };
}
