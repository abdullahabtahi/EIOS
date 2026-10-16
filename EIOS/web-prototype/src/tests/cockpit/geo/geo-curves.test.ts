import { describe, it, expect } from 'vitest';
import { curvePath, fadeAlong, wrapCopies } from '@/components/cockpit/geo/geo-curves';
import type { LngLat } from '@/components/cockpit/geo/geo-types';

const LAGOS: LngLat = [3.4, 6.5];
const YANGON: LngLat = [96.2, 16.8];
const TOKYO: LngLat = [139.7, 35.7];
const HONOLULU: LngLat = [-157.9, 21.3];

/** Which side of the straight chord the middle of the curve falls on: positive is left of the direction of travel. */
const side = (path: readonly (readonly [number, number])[]): number => {
  const a = path[0];
  const b = path[path.length - 1];
  const m = path[Math.floor(path.length / 2)];
  return (b[0] - a[0]) * (m[1] - a[1]) - (b[1] - a[1]) * (m[0] - a[0]);
};

describe('curvePath', () => {
  it('starts and ends exactly on the two countries', () => {
    const path = curvePath(LAGOS, YANGON);
    expect(path[0]).toEqual([3.4, 6.5]);
    expect(path[path.length - 1]).toEqual([96.2, 16.8]);
    expect(path.length).toBeGreaterThan(8);
  });

  it('keeps a bend small enough to read as a route, not a loop', () => {
    const path = curvePath(LAGOS, YANGON);
    const lngs = path.map((p) => p[0]);
    expect(Math.min(...lngs)).toBeGreaterThan(3.4 - 15);
    expect(Math.max(...lngs)).toBeLessThan(96.2 + 15);
  });

  it('bends the two directions of one pair to opposite sides, so they do not sit on each other', () => {
    // Both are measured against the same chord, Lagos to Yangon, so the reversed path is read backwards.
    expect(side(curvePath(LAGOS, YANGON)) * side([...curvePath(YANGON, LAGOS)].reverse())).toBeLessThan(0);
  });

  it('crosses the antimeridian the short way instead of the whole map the long way', () => {
    const path = curvePath(TOKYO, HONOLULU);
    expect(Math.max(...path.map((p) => p[0]))).toBeGreaterThan(180);
    expect(path[path.length - 1][0]).toBeCloseTo(202.1, 1);
    expect(Math.min(...path.map((p) => p[0]))).toBeGreaterThan(130);
  });

  it('draws a copy one world over for a path that leaves the first world, so it shows on either side of the edge', () => {
    const crossing = curvePath(TOKYO, HONOLULU);
    const copies = wrapCopies(crossing);
    expect(copies).toHaveLength(2);
    expect(copies[1][0][0]).toBeCloseTo(crossing[0][0] - 360, 6);
    expect(wrapCopies(curvePath(LAGOS, YANGON))).toHaveLength(1);
  });

  it('stays inside the latitudes a web map can draw', () => {
    const path = curvePath([0, 78], [170, 79]);
    expect(path.every((p) => Math.abs(p[1]) <= 80)).toBe(true);
  });

  it('does not mutate its inputs', () => {
    const from: LngLat = [1, 2];
    const to: LngLat = [200, 3];
    curvePath(from, to);
    expect(from).toEqual([1, 2]);
    expect(to).toEqual([200, 3]);
  });
});

describe('fadeAlong', () => {
  it('runs from faint at the origin to full at the destination, which is how direction reads', () => {
    const colors = fadeAlong([168, 42, 42, 220], 10);
    expect(colors).toHaveLength(10);
    expect(colors[0][3]).toBeLessThan(colors[9][3]);
    expect(colors[9]).toEqual([168, 42, 42, 220]);
    expect(colors[0].slice(0, 3)).toEqual([168, 42, 42]);
  });
});
