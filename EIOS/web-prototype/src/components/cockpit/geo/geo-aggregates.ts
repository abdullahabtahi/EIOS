import type { FatfList, GeoEvidence, GeoReference, GeoSummary, ReferenceCountry } from './geo-types';

const DEFAULT_TOP_N = 5;

/** Deterministic roll-ups for the widgets; the same numbers the map draws, never a second source. */
export function summarize(evidence: GeoEvidence, topN: number = DEFAULT_TOP_N): GeoSummary {
  const { corridors, mismatches } = evidence;
  const volumeByTier = corridors.reduce(
    (acc, c) => ({ ...acc, [c.riskTier]: acc[c.riskTier] + c.volumeUsd }),
    { low: 0, medium: 0, high: 0 },
  );
  return {
    corridorVolumeUsd: corridors.length === 0 ? null : corridors.reduce((t, c) => t + c.volumeUsd, 0),
    volumeByTier,
    topCorridors: [...corridors].sort((a, b) => b.volumeUsd - a.volumeUsd).slice(0, topN),
    mismatchCount: mismatches.length,
  };
}

export interface ReferenceSummary {
  readonly fatf: Readonly<Record<FatfList, number>>;
  readonly topOffshore: readonly ReferenceCountry[];
}

/** Roll-ups of the reference layer for the widgets; null when there is no reference layer (no data, not zero). */
export function summarizeReference(reference: GeoReference | null, topN: number = 6): ReferenceSummary | null {
  if (!reference) return null;
  const fatf = reference.countries.reduce(
    (acc, c) => (c.fatf_list ? { ...acc, [c.fatf_list]: acc[c.fatf_list] + 1 } : acc),
    { call_for_action: 0, increased_monitoring: 0 } as Record<FatfList, number>,
  );
  const topOffshore = reference.countries
    .filter((c) => (c.entities_incorporated ?? 0) > 0)
    .sort((a, b) => (b.entities_incorporated ?? 0) - (a.entities_incorporated ?? 0))
    .slice(0, topN);
  return { fatf, topOffshore };
}
