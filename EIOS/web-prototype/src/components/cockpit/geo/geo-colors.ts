/**
 * The cockpit's state colours and inks, written out for deck.gl, which takes numbers and cannot read CSS variables. The
 * names are the stylesheet's own (`--color-<name>`), and a test fails when one drifts from `globals.css`.
 */
export const GEO_TOKENS = {
  'cx-bad': '#a82a2a',
  'cx-warn': '#a66321',
  'cx-accent': '#106ba3',
  'cx-ink': '#182026',
  'cx-muted': '#5c7080',
  'cx-faint': '#8a9ba8',
} as const;

export type Rgba = [number, number, number, number];

/** A token as deck.gl colour with the given opacity (0 to 255). */
export function rgba(name: keyof typeof GEO_TOKENS, alpha: number): Rgba {
  const hex = GEO_TOKENS[name].slice(1);
  const [r, g, b] = [0, 2, 4].map((i) => Number.parseInt(hex.slice(i, i + 2), 16));
  return [r, g, b, alpha];
}
