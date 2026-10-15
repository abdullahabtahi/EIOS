import type { FlowCorridor, GeoFlows, MismatchPair, RiskTier } from './geo-types';

/** [ASSUMPTION] arcs drawn per kind, chosen so the map stays readable; the list keeps every row. High and medium have their own budget so one cannot crowd out the other. */
export const ARC_BUDGET = { high: 10, medium: 4, other: 4 } as const;
export const MAX_MISMATCH_PAIRS = 10;

const TIER_RANK: Readonly<Record<RiskTier, number>> = { high: 2, medium: 1, low: 0 };
export const isElevated = (c: FlowCorridor): boolean => c.tier === 'high' || c.tier === 'medium';

/**
 * One order for the map and the list, so the arc you see is the row you can click: elevated corridors first, high
 * before medium, then by volume; the rest by volume. An unrated corridor (tier null) is never ranked as elevated.
 */
export function rankedCorridors(flows: GeoFlows): readonly FlowCorridor[] {
  const byVolume = (a: FlowCorridor, b: FlowCorridor) => b.volume_usd - a.volume_usd;
  const elevated = flows.corridors
    .filter(isElevated)
    .sort((a, b) => TIER_RANK[b.tier as RiskTier] - TIER_RANK[a.tier as RiskTier] || byVolume(a, b));
  return [...elevated, ...flows.corridors.filter((c) => !isElevated(c)).sort(byVolume)];
}

/** Flagged country pairs, the most accounts first. */
export function rankedPairs(flows: GeoFlows): readonly MismatchPair[] {
  return [...flows.mismatch_pairs].sort((a, b) => b.accounts - a.accounts || b.volume_usd - a.volume_usd);
}

/** The corridors the map draws: the top of each tier's ranking, then the largest of the rest. */
export function shownCorridors(flows: GeoFlows): readonly FlowCorridor[] {
  const ranked = rankedCorridors(flows);
  const top = (keep: (c: FlowCorridor) => boolean, n: number) => ranked.filter(keep).slice(0, n);
  return [
    ...top((c) => c.tier === 'high', ARC_BUDGET.high),
    ...top((c) => c.tier === 'medium', ARC_BUDGET.medium),
    ...top((c) => !isElevated(c), ARC_BUDGET.other),
  ];
}

/** Which arc colours are on the map, so the legend lists only those. */
export function drawnKinds(flows: GeoFlows): ReadonlySet<'high' | 'medium' | 'other'> {
  return new Set(shownCorridors(flows).map((c) => (c.tier === 'high' || c.tier === 'medium' ? c.tier : 'other')));
}

export function shownPairs(flows: GeoFlows): readonly MismatchPair[] {
  return rankedPairs(flows).slice(0, MAX_MISMATCH_PAIRS);
}

export const corridorId = (c: Pick<FlowCorridor, 'origin' | 'destination'>): string => `${c.origin}>${c.destination}`;
export const pairId = (p: Pick<MismatchPair, 'kyc_country' | 'ip_country'>): string => `${p.kyc_country}>${p.ip_country}`;
