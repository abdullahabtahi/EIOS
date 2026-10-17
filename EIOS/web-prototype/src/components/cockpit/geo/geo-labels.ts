import type { LngLat } from './geo-types';

export interface PlacedLabel {
  readonly name: string;
  readonly position: LngLat;
  /** Which name survives when two would overlap: higher wins. */
  readonly priority: number;
}

/** [ASSUMPTION] a label's footprint in pixels: about this wide per character at 12px semibold, this tall, with a little air around it. */
const CHAR_PX = 7;
const HEIGHT_PX = 16;
const GAP_PX = 4;
/** The label is drawn this far above its anchor (geo-layers LABEL_LIFT_PX), so its box is centred this far up. */
const LIFT_PX = 16;
const TILE_PX = 256;

/** Where a coordinate falls on the whole-world Web Mercator canvas at a zoom, in pixels. */
function worldPixel([lng, lat]: LngLat, zoom: number): { x: number; y: number } {
  const scale = TILE_PX * 2 ** zoom;
  const clamped = Math.max(-85, Math.min(85, lat));
  const sin = Math.sin((clamped * Math.PI) / 180);
  return { x: ((lng + 180) / 360) * scale, y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * scale };
}

interface Box {
  readonly left: number;
  readonly right: number;
  readonly top: number;
  readonly bottom: number;
}

function boxOf(label: PlacedLabel, zoom: number): Box {
  const { x, y } = worldPixel(label.position, zoom);
  const half = (label.name.length * CHAR_PX) / 2 + GAP_PX;
  return { left: x - half, right: x + half, top: y - LIFT_PX - HEIGHT_PX / 2 - GAP_PX, bottom: y - LIFT_PX + HEIGHT_PX / 2 + GAP_PX };
}

const overlaps = (a: Box, b: Box): boolean => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

/**
 * The labels that fit without printing over each other at this zoom, the highest priority first claiming its place. A hidden
 * name comes back when zooming in separates it from its neighbour. Deck.gl's own collision filter was tried first; in the
 * interleaved Google Maps overlay it hid every label, so the footprints are computed here, where they can be tested.
 */
export function declutterLabels<T extends PlacedLabel>(labels: readonly T[], zoom: number): readonly T[] {
  const kept: { label: T; box: Box }[] = [];
  for (const label of [...labels].sort((a, b) => b.priority - a.priority)) {
    const box = boxOf(label, zoom);
    if (!kept.some((k) => overlaps(k.box, box))) kept.push({ label, box });
  }
  return kept.map((k) => k.label);
}
