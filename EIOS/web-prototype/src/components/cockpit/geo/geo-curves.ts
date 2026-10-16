import type { LngLat } from './geo-types';

type Point = [number, number];
type Rgba = [number, number, number, number];

/** [ASSUMPTION] how far a route bends from the straight line, as a share of its length; small enough to read as a route, not a loop. */
const BEND = 0.14;
const STEPS = 32;
const MAX_LAT = 80;
/** [ASSUMPTION] how faint a route starts at its origin, as a share of its colour's alpha; it reaches full alpha at the destination. */
const FADE_FROM = 0.2;
const HALF_WORLD = 180;
const WORLD = 360;

const clampLat = (lat: number): number => Math.max(-MAX_LAT, Math.min(MAX_LAT, lat));

/**
 * A route from one country to another as a gentle curve bending to the left of travel, so the two directions of a pair
 * part instead of lying on each other. A route that would cross the map the long way goes over the antimeridian instead:
 * the end may then sit beyond 180 degrees of longitude, which the map draws one world over.
 */
export function curvePath(source: LngLat, target: LngLat): Point[] {
  const [x0, y0] = source;
  const dx = target[0] - x0;
  const x1 = dx > HALF_WORLD ? target[0] - WORLD : dx < -HALF_WORLD ? target[0] + WORLD : target[0];
  const y1 = target[1];
  const ex = x1 - x0;
  const ey = y1 - y0;
  // The control point sits off the midpoint along the left-hand normal (-ey, ex).
  const cx = (x0 + x1) / 2 - ey * BEND;
  const cy = (y0 + y1) / 2 + ex * BEND;
  const points: Point[] = [];
  for (let i = 0; i <= STEPS; i += 1) {
    const t = i / STEPS;
    const a = (1 - t) * (1 - t);
    const b = 2 * (1 - t) * t;
    const c = t * t;
    points.push([a * x0 + b * cx + c * x1, clampLat(a * y0 + b * cy + c * y1)]);
  }
  points[0] = [x0, y0];
  points[STEPS] = [x1, y1];
  return points;
}

/** The path, and the same path one world over when it leaves the first world, so it shows on either side of the map's edge. */
export function wrapCopies(path: readonly Point[]): readonly (readonly Point[])[] {
  const lngs = path.map((p) => p[0]);
  const shift = Math.max(...lngs) > HALF_WORLD ? -WORLD : Math.min(...lngs) < -HALF_WORLD ? WORLD : 0;
  return shift === 0 ? [path] : [path, path.map(([x, y]): Point => [x + shift, y])];
}

/** One colour per vertex, faint at the origin and full at the destination: the direction of money is read from the line itself. */
export function fadeAlong(color: Readonly<Rgba>, count: number): Rgba[] {
  const [r, g, b, a] = color;
  return Array.from({ length: count }, (_, i): Rgba => {
    const t = count > 1 ? i / (count - 1) : 1;
    return [r, g, b, Math.round(a * (FADE_FROM + (1 - FADE_FROM) * t))];
  });
}
