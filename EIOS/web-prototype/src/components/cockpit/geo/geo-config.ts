export interface MapsConfig {
  readonly apiKey: string;
  /** A cloud-styled Map ID when configured; otherwise null and the map uses the built-in muted light style. */
  readonly mapId: string | null;
}

/**
 * Google Maps browser config. `NEXT_PUBLIC_*` values reach the browser only as written-out
 * `process.env.NEXT_PUBLIC_X` references, so they are read here literally, never through a variable.
 * Returns null when the key is absent: the view then says so instead of rendering a blank map.
 */
export function readMapsConfig(): MapsConfig | null {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  if (!apiKey) return null;
  return { apiKey, mapId: process.env.NEXT_PUBLIC_GOOGLE_MAP_ID || null };
}
