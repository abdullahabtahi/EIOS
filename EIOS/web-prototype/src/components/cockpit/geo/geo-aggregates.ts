import type { FatfList, GeoFlows, GeoReference, GeoSummary } from './geo-types';

/** Roll-ups of the engine flows for the summary: the same numbers the map draws, never a second source. Null without flows. */
export function summarize(flows: GeoFlows | null): GeoSummary | null {
  if (!flows) return null;
  return {
    corridorVolumeUsd: flows.corridors.length === 0 ? null : flows.corridors.reduce((t, c) => t + c.volume_usd, 0),
    exposure: flows.exposure,
    flaggedAccounts: flows.mismatch_pairs.reduce((t, p) => t + p.accounts, 0),
  };
}

export interface ReferenceSummary {
  readonly fatf: Readonly<Record<FatfList, number>>;
}

/** Roll-ups of the reference layer for the summary; null when there is no reference layer (no data, not zero). */
export function summarizeReference(reference: GeoReference | null): ReferenceSummary | null {
  if (!reference) return null;
  const fatf = reference.countries.reduce(
    (acc, c) => (c.fatf_list ? { ...acc, [c.fatf_list]: acc[c.fatf_list] + 1 } : acc),
    { call_for_action: 0, increased_monitoring: 0 } as Record<FatfList, number>,
  );
  return { fatf };
}
