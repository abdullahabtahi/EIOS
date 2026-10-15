import { formatUsd, nameOf } from './geo-format';
import { corridorId, pairId, rankedCorridors, rankedPairs } from './geo-rank';
import type { GeoFlows, GeoReference, GeoSelection, RiskTier } from './geo-types';
import type { ViewId } from './geo-views';

/** A place to start: one row of the "where to look first" list, selectable like a mark on the map. */
export interface Lead {
  readonly key: string;
  readonly selection: NonNullable<GeoSelection>;
  readonly title: string;
  readonly detail: string;
  /** Only elevated tiers are flagged; everything else stays quiet. */
  readonly tier: Extract<RiskTier, 'high' | 'medium'> | null;
  readonly group?: string;
}

const COUNT = new Intl.NumberFormat('en-US');
const plural = (n: number, one: string, many: string = `${one}s`): string => `${COUNT.format(n)} ${n === 1 ? one : many}`;
const TOP_OFFSHORE = 5;

function corridorLeads(flows: GeoFlows, reference: GeoReference | null): readonly Lead[] {
  return rankedCorridors(flows).map((c) => ({
    key: `corridor:${corridorId(c)}`,
    selection: { kind: 'corridor', id: corridorId(c) },
    title: `${nameOf(reference, c.origin)} → ${nameOf(reference, c.destination)}`,
    detail: `${formatUsd(c.volume_usd)} · ${plural(c.accounts, 'account')}`,
    tier: c.tier === 'high' || c.tier === 'medium' ? c.tier : null,
  }));
}

function loginLeads(flows: GeoFlows, reference: GeoReference | null): readonly Lead[] {
  return rankedPairs(flows).map((p) => ({
    key: `mismatch:${pairId(p)}`,
    selection: { kind: 'mismatch', id: pairId(p) },
    title: `${nameOf(reference, p.kyc_country)} → ${nameOf(reference, p.ip_country)}`,
    detail: `${plural(p.accounts, 'account')} · ${COUNT.format(p.foreign_events)} of ${COUNT.format(p.events)} logins abroad`,
    tier: null,
  }));
}

function jurisdictionLeads(reference: GeoReference): readonly Lead[] {
  const named = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);
  const callForAction = reference.countries.filter((c) => c.fatf_list === 'call_for_action').sort(named);
  const offshore = reference.countries
    .filter((c) => (c.entities_incorporated ?? 0) > 0)
    .sort((a, b) => (b.entities_incorporated ?? 0) - (a.entities_incorporated ?? 0))
    .slice(0, TOP_OFFSHORE);
  return [
    ...callForAction.map((c) => ({
      key: `fatf:${c.iso2}`,
      selection: { kind: 'country', id: c.iso2 } as const,
      title: c.name,
      detail: 'FATF call for action',
      tier: 'high' as const,
      group: 'On the FATF call-for-action list',
    })),
    ...offshore.map((c) => ({
      key: `offshore:${c.iso2}`,
      selection: { kind: 'country', id: c.iso2 } as const,
      title: c.name,
      detail: `${COUNT.format(c.entities_incorporated ?? 0)} offshore entities incorporated`,
      tier: null,
      group: 'Largest offshore centres',
    })),
  ];
}

/**
 * The ranked list for a view, from the same data and order the map draws. Null when the data the view needs is
 * absent (no data, not an empty list); an empty array means it was measured and there is nothing to list.
 */
export function leadsFor(view: ViewId, flows: GeoFlows | null, reference: GeoReference | null): readonly Lead[] | null {
  if (view === 'jurisdictions') return reference ? jurisdictionLeads(reference) : null;
  if (!flows) return null;
  return view === 'corridors' ? corridorLeads(flows, reference) : loginLeads(flows, reference);
}
