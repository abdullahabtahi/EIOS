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
export function cameraFor(selection: GeoSelection, flows: GeoFlows | null, reference: GeoReference | null): CameraTarget | null {
  if (!selection || !reference) return null;
  const at = (code: string): LngLat | undefined => reference.countries.find((c) => c.iso2 === code)?.position;
  if (selection.kind === 'country') {
    const p = at(selection.id);
    return p ? { kind: 'point', center: { lat: p[1], lng: p[0] }, zoom: COUNTRY_ZOOM } : null;
  }
  if (!flows) return null;
  const [from, to] = selection.id.split('>');
  const a = at(from);
  const b = at(to);
  return a && b ? between(a, b) : null;
}
