import type { BasisId } from './geo-basis';
import { FATF_TEXT, formatUsd, nameOf } from './geo-format';
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
const TOP_BASEL = 10;

function corridorLeads(flows: GeoFlows, reference: GeoReference | null): readonly Lead[] {
  return rankedCorridors(flows).map((c) => ({
    key: `corridor:${corridorId(c)}`,
    selection: { kind: 'corridor', id: corridorId(c) },
    title: `${nameOf(reference, c.origin)} → ${nameOf(reference, c.destination)}`,
    detail: `${formatUsd(c.volume_usd)} · ${plural(c.accounts, 'account')}`,
    tier: c.tier === 'high' || c.tier === 'medium' ? c.tier : null,
  }));
}

function gatewayLeads(flows: GeoFlows, reference: GeoReference | null): readonly Lead[] {
  return (flows.gateways ?? []).map((g): Lead => ({
    key: `gateway:${g.gateway_id}`,
    selection: { kind: 'gateway', id: g.gateway_id },
    title: `Shared exit in ${nameOf(reference, g.country)}`,
    detail: `${plural(g.accounts, 'account')} from ${plural(g.home_countries.length, 'country', 'countries')} · ${plural(g.impossible_jumps, 'impossible jump')}`,
    tier: 'high',
    group: 'Shared foreign exits',
  }));
}

function loginLeads(flows: GeoFlows, reference: GeoReference | null): readonly Lead[] {
  const exits = gatewayLeads(flows, reference);
  const pairs = rankedPairs(flows).map((p): Lead => ({
    key: `mismatch:${pairId(p)}`,
    selection: { kind: 'mismatch', id: pairId(p) },
    title: `${nameOf(reference, p.kyc_country)} → ${nameOf(reference, p.ip_country)}`,
    detail: `${plural(p.accounts, 'account')} · ${COUNT.format(p.foreign_events)} of ${COUNT.format(p.events)} logins abroad`,
    tier: null,
    ...(exits.length > 0 ? { group: 'Registered here, logging in there' } : {}),
  }));
  return [...exits, ...pairs];
}

function jurisdictionLeads(reference: GeoReference): readonly Lead[] {
  const callForAction = reference.countries.filter((c) => c.fatf_list === 'call_for_action').sort(byName);
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

const byName = (a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name);

function euLeads(reference: GeoReference): readonly Lead[] {
  const listed = reference.countries.filter((c) => c.eu_high_risk).sort(byName);
  const lead = (c: GeoReference['countries'][number], group: string): Lead => ({
    key: `eu:${c.iso2}`,
    selection: { kind: 'country', id: c.iso2 },
    title: c.name,
    detail: c.fatf_list ? `EU list · FATF ${FATF_TEXT[c.fatf_list].toLowerCase()}` : 'EU list only',
    tier: 'medium',
    group,
  });
  return [
    ...listed.filter((c) => !c.fatf_list).map((c) => lead(c, 'On the EU list, not on the FATF lists')),
    ...listed.filter((c) => c.fatf_list).map((c) => lead(c, 'On the EU list and a FATF list')),
  ];
}

function baselLeads(reference: GeoReference): readonly Lead[] {
  return reference.countries
    .flatMap((c) => (c.basel ? [{ c, b: c.basel }] : []))
    .sort((x, y) => x.b.rank - y.b.rank)
    .slice(0, TOP_BASEL)
    .map(({ c, b }): Lead => ({
      key: `basel:${c.iso2}`,
      selection: { kind: 'country', id: c.iso2 },
      title: c.name,
      detail: `${b.score.toFixed(2)} of 10 · rank ${b.rank} of ${b.of}`,
      tier: b.band === 'higher' ? 'high' : b.band === 'medium' ? 'medium' : null,
      group: 'Highest Basel AML Index scores',
    }));
}

/**
 * The ranked list for a view, from the same data and order the map draws. Null when the data the view needs is
 * absent (no data, not an empty list); an empty array means it was measured and there is nothing to list.
 */
export function leadsFor(view: ViewId, flows: GeoFlows | null, reference: GeoReference | null, basis: BasisId = 'fatf'): readonly Lead[] | null {
  if (view === 'jurisdictions') {
    if (!reference) return null;
    return basis === 'eu' ? euLeads(reference) : basis === 'basel' ? baselLeads(reference) : jurisdictionLeads(reference);
  }
  if (!flows) return null;
  return view === 'corridors' ? corridorLeads(flows, reference) : loginLeads(flows, reference);
}
