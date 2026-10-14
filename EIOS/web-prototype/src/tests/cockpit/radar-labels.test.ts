import { describe, it, expect } from 'vitest';
import { visibleLabelIds, type LabelCandidate } from '@/components/cockpit/common/radar-labels';

const node = (id: string, cx: number, cy: number, priority: number): LabelCandidate => ({
  id,
  cx,
  cy,
  side: 'start',
  priority,
});

describe('visibleLabelIds', () => {
  it('shows every label when nodes are far apart', () => {
    const shown = visibleLabelIds([node('PTR-1', 50, 50, 1), node('PTR-2', 300, 200, 2)], new Set());
    expect([...shown].sort()).toEqual(['PTR-1', 'PTR-2']);
  });

  it('drops the lower-priority label when two collide', () => {
    const shown = visibleLabelIds([node('PTR-607', 100, 100, 5), node('PTR-128', 104, 103, 1)], new Set());
    expect(shown.has('PTR-607')).toBe(true);
    expect(shown.has('PTR-128')).toBe(false);
  });

  it('always shows a pinned label, even over a collision', () => {
    const shown = visibleLabelIds([node('PTR-607', 100, 100, 5), node('PTR-128', 104, 103, 1)], new Set(['PTR-128']));
    expect(shown.has('PTR-128')).toBe(true);
  });

  it('hides a lower-priority label that would sit on a higher-priority node', () => {
    const shown = visibleLabelIds([node('PTR-1', 100, 100, 5), node('PTR-2', 60, 100, 1)], new Set());
    expect(shown.has('PTR-1')).toBe(true);
    expect(shown.has('PTR-2')).toBe(false);
  });

  it('keeps labels out of reserved areas such as quadrant captions', () => {
    const reserved = [{ x0: 90, y0: 90, x1: 200, y1: 110 }];
    const shown = visibleLabelIds([node('PTR-1', 100, 100, 5)], new Set(), reserved);
    expect(shown.has('PTR-1')).toBe(false);
  });

  it('does not mutate its input', () => {
    const input = [node('A-1', 10, 10, 1), node('B-2', 200, 10, 9)];
    visibleLabelIds(input, new Set());
    expect(input.map((c) => c.id)).toEqual(['A-1', 'B-2']);
  });
});
