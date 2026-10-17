import type { Box, Point } from './geo-chat-dock';

const OFFSET = 14;

/**
 * Where a card of this size goes beside a pointer: right and below by default, flipped to the other side of the pointer
 * when its real width or height would cross the map's edge, and held inside the map as a last resort.
 */
export function placeTooltip(point: Point, size: Box, bounds: Box): { left: number; top: number } {
  const flipX = point.x + OFFSET + size.width > bounds.width;
  const flipY = point.y + OFFSET + size.height > bounds.height;
  const left = flipX ? point.x - OFFSET - size.width : point.x + OFFSET;
  const top = flipY ? point.y - OFFSET - size.height : point.y + OFFSET;
  const within = (n: number, extent: number, limit: number) => Math.max(0, Math.min(n, limit - extent));
  return { left: within(left, size.width, bounds.width), top: within(top, size.height, bounds.height) };
}
