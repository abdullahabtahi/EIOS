import type { GeoFlows, GeoReference, GeoSelection, LngLat } from './geo-types';

export type CameraTarget =
  | { readonly kind: 'bounds'; readonly north: number; readonly south: number; readonly east: number; readonly west: number }
  | { readonly kind: 'point'; readonly center: { readonly lat: number; readonly lng: number }; readonly zoom: number };

/** [ASSUMPTION] zoom that frames one country, and the smallest span (degrees) a route is framed at, so two close ends are not zoomed in to a blur. */
export const COUNTRY_ZOOM = 5;
export const MIN_SPAN_DEG = 12;

function between(a: LngLat, b: LngLat): CameraTarget {
  const pad = (lo: number, hi: number) => {
    const extra = Math.max(0, MIN_SPAN_DEG - (hi - lo)) / 2;
    return [lo - extra, hi + extra] as const;
  };
  const [west, east] = pad(Math.min(a[0], b[0]), Math.max(a[0], b[0]));
  const [south, north] = pad(Math.min(a[1], b[1]), Math.max(a[1], b[1]));
  return { kind: 'bounds', north: Math.min(north, 80), south: Math.max(south, -80), east, west };
}

/**
 * Where to move the camera when an analyst picks a lead: both ends of a route, or the country. Null when the
 * reference layer cannot place it, so nothing moves rather than the map jumping somewhere invented.
 */
/** Frame a set of countries (a gateway and its users' homes, an account's login countries); null if none can be placed. */
export function cameraForCodes(codes: readonly string[], reference: GeoReference | null): CameraTarget | null {
  if (!reference) return null;
  const points = codes
    .map((code) => reference.countries.find((c) => c.iso2 === code)?.position)
    .filter((p): p is LngLat => p !== undefined);
  if (points.length === 0) return null;
  if (points.length === 1) return { kind: 'point', center: { lat: points[0][1], lng: points[0][0] }, zoom: COUNTRY_ZOOM };
  const lngs = points.map((p) => p[0]);
  const lats = points.map((p) => p[1]);
  return between([Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]);
}

export function cameraFor(selection: GeoSelection, flows: GeoFlows | null, reference: GeoReference | null): CameraTarget | null {
  if (!selection || !reference) return null;
  if (selection.kind === 'gateway') {
    const g = flows?.gateways?.find((x) => x.gateway_id === selection.id);
    return g ? cameraForCodes([g.country, ...g.home_countries.map((h) => h.iso2)], reference) : null;
  }
  if (selection.kind === 'account') return null; // framed once the account's evidence arrives
  const at = (code: string): LngLat | undefined => reference.countries.find((c) => c.iso2 === code)?.position;
  if (selection.kind === 'country') {
    const p = at(selection.id);
    return p ? { kind: 'point', center: { lat: p[1], lng: p[0] }, zoom: COUNTRY_ZOOM } : null;
  }
  if (!flows || (selection.kind !== 'corridor' && selection.kind !== 'mismatch')) return null;
  const [from, to] = selection.id.split('>');
  const a = at(from);
  const b = at(to);
  return a && b ? between(a, b) : null;
}
