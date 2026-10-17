import { describe, it, expect } from 'vitest';
import { placeTooltip } from '@/components/cockpit/geo/geo-tooltip-place';

const BOUNDS = { width: 800, height: 600 };
const SIZE = { width: 248, height: 110 };

describe('where the tooltip goes', () => {
  it('sits beside the pointer, to the right and below, when there is room', () => {
    expect(placeTooltip({ x: 100, y: 100 }, SIZE, BOUNDS)).toEqual({ left: 114, top: 114 });
  });

  it('flips to the left of the pointer at the right edge, by its real width', () => {
    expect(placeTooltip({ x: 700, y: 100 }, SIZE, BOUNDS).left).toBe(700 - 14 - SIZE.width);
  });

  it('flips above the pointer at the bottom edge, by its real height, so a tall card does not run off', () => {
    const tall = { width: 248, height: 190 };
    expect(placeTooltip({ x: 100, y: 500 }, tall, BOUNDS).top).toBe(500 - 14 - tall.height);
    // a short card flips to just as far above as it is tall, not a fixed guess
    expect(placeTooltip({ x: 100, y: 560 }, SIZE, BOUNDS).top).toBe(560 - 14 - SIZE.height);
  });

  it('never leaves the map, even in a corner', () => {
    const p = placeTooltip({ x: 790, y: 590 }, SIZE, BOUNDS);
    expect(p.left).toBeGreaterThanOrEqual(0);
    expect(p.top).toBeGreaterThanOrEqual(0);
    expect(p.left + SIZE.width).toBeLessThanOrEqual(BOUNDS.width);
    expect(p.top + SIZE.height).toBeLessThanOrEqual(BOUNDS.height);
  });

  it('stays at the top left of a map smaller than the card', () => {
    expect(placeTooltip({ x: 10, y: 10 }, SIZE, { width: 100, height: 60 })).toEqual({ left: 0, top: 0 });
  });
});
