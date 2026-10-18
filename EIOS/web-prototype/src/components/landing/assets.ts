/**
 * Landing rasters live in public/ and are served with a one-year immutable cache (next.config.ts),
 * so a changed file needs a new version here or visitors keep the old one.
 */
export const LANDING_ASSET_VERSION = "1";

export const landingAsset = (path: string): string => `/landing/${path}?v=${LANDING_ASSET_VERSION}`;

/** `1200w, 1800w, 2400w` style srcset for a raster that ships `-1200`, `-1800` and full-size files. */
export const landingSrcSet = (stem: string, widths: readonly number[], fullWidth: number): string =>
  [...widths.map((w) => `${landingAsset(`${stem}-${w}.webp`)} ${w}w`), `${landingAsset(`${stem}.webp`)} ${fullWidth}w`].join(", ");
