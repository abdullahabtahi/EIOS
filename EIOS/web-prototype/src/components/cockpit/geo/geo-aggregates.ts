import type { FatfList, GeoFlows, GeoReference, GeoSummary, ReferenceCountry } from './geo-types';

const DEFAULT_TOP_N = 5;

/** Roll-ups of the engine flows for the widgets: the same numbers the map draws, never a second source. Null without flows. */
export function summarize(flows: GeoFlows | null, topN: number = DEFAULT_TOP_N): GeoSummary | null {
  if (!flows) return null;
  return {
    corridorVolumeUsd: flows.corridors.length === 0 ? null : flows.corridors.reduce((t, c) => t + c.volume_usd, 0),
    exposure: flows.exposure,
    topCorridors: [...flows.corridors].sort((a, b) => b.volume_usd - a.volume_usd).slice(0, topN),
    flaggedAccounts: flows.mismatch_pairs.reduce((t, p) => t + p.accounts, 0),
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
