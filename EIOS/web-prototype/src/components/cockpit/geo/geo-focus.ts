import type { GeoFlows, GeoReference } from './geo-types';

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
