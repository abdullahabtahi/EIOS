import type { GeoFlows, GeoReference } from './geo-types';
import type { ViewId } from './geo-views';

export interface MapFocus {
  readonly center: { readonly lat: number; readonly lng: number };
  readonly zoom: number;
}

/** [ASSUMPTION] zoom that frames a multi-country region (the world is zoom 2). */
export const REGION_ZOOM = 3;

/**
 * Where to open the map: the volume-weighted centre of the corridors' end countries, so the view starts on the
 * money, not on empty ocean. Null when there are no flows or the reference layer cannot place them.
 */
export function focusOf(flows: GeoFlows | null, reference: GeoReference | null): MapFocus | null {
  if (!flows || !reference) return null;
  const at = new Map(reference.countries.map((c) => [c.iso2, c.position]));
  let weight = 0;
  let lng = 0;
  let lat = 0;
  for (const c of flows.corridors) {
    for (const code of [c.origin, c.destination]) {
      const p = at.get(code);
      if (!p) continue;
      weight += c.volume_usd;
      lng += p[0] * c.volume_usd;
      lat += p[1] * c.volume_usd;
    }
  }
  return weight > 0 ? { center: { lat: lat / weight, lng: lng / weight }, zoom: REGION_ZOOM } : null;
}

/** [ASSUMPTION] zoom for the view that shows the whole world (jurisdictions are scattered across it). */
const WORLD_FOCUS: MapFocus = { center: { lat: 22, lng: 15 }, zoom: 2 };

/** The centre of a set of country pairs, each pair weighted; null when none can be placed. */
function weightedCentre(rows: readonly { readonly codes: readonly string[]; readonly weight: number }[], reference: GeoReference): MapFocus | null {
  const at = new Map(reference.countries.map((c) => [c.iso2, c.position]));
  let weight = 0;
  let lng = 0;
  let lat = 0;
  for (const row of rows) {
    for (const code of row.codes) {
      const p = at.get(code);
      if (!p) continue;
      weight += row.weight;
      lng += p[0] * row.weight;
      lat += p[1] * row.weight;
    }
  }
  return weight > 0 ? { center: { lat: lat / weight, lng: lng / weight }, zoom: REGION_ZOOM } : null;
}

/** Where each view opens: the money for corridors, the flagged accounts for logins, the whole world for jurisdictions. */
export function focusFor(view: ViewId, flows: GeoFlows | null, reference: GeoReference | null): MapFocus | null {
  if (view === 'jurisdictions') return WORLD_FOCUS;
  if (!flows || !reference) return null;
  if (view === 'corridors') return focusOf(flows, reference);
  return weightedCentre(flows.mismatch_pairs.map((p) => ({ codes: [p.kyc_country, p.ip_country], weight: p.accounts })), reference);
}
