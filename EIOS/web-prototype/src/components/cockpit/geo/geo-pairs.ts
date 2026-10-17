import type { FlowCorridor, RiskTier } from './geo-types';

/** The two directions of one country pair as a single route: the bigger direction leads, and the width reads from both together. */
export interface CorridorPair {
  readonly lead: FlowCorridor;
  readonly back: FlowCorridor | null;
  readonly gross: number;
  /** The higher of the two directions' tiers; null only when neither is rated. */
  readonly tier: RiskTier | null;
}

const RANK: Readonly<Record<RiskTier, number>> = { low: 0, medium: 1, high: 2 };
const key = (c: FlowCorridor): string => [c.origin, c.destination].sort((a, b) => a.localeCompare(b)).join('|');

function higher(a: RiskTier | null, b: RiskTier | null): RiskTier | null {
  if (a === null) return b;
  if (b === null) return a;
  return RANK[a] >= RANK[b] ? a : b;
}

/** Folds the drawn corridors into routes, looking up each one's opposite direction among all corridors. Order follows the drawn list. */
export function pairUp(drawn: readonly FlowCorridor[], all: readonly FlowCorridor[]): readonly CorridorPair[] {
  const opposite = new Map(all.map((c) => [`${c.destination}>${c.origin}`, c]));
  const seen = new Set<string>();
  return drawn.flatMap((c) => {
    if (seen.has(key(c))) return [];
    seen.add(key(c));
    const back = opposite.get(`${c.origin}>${c.destination}`) ?? null;
    const [lead, other] = back && back.volume_usd > c.volume_usd ? [back, c] : [c, back];
    return [{ lead, back: other, gross: c.volume_usd + (back?.volume_usd ?? 0), tier: higher(c.tier, back?.tier ?? null) }];
  });
}

/** Countries that at least `min` routes meet: where the lines converge, drawn as one node instead of a knot. */
export function hubsOf(pairs: readonly CorridorPair[], min: number): readonly { readonly iso2: string; readonly spokes: number; readonly tier: RiskTier | null }[] {
  const counts = new Map<string, { spokes: number; tier: RiskTier | null }>();
  for (const p of pairs) {
    for (const code of [p.lead.origin, p.lead.destination]) {
      const seen = counts.get(code) ?? { spokes: 0, tier: null };
      counts.set(code, { spokes: seen.spokes + 1, tier: higher(seen.tier, p.tier) });
    }
  }
  return [...counts.entries()].filter(([, v]) => v.spokes >= min).map(([iso2, v]) => ({ iso2, ...v }));
}
