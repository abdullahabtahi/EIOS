import { describe, it, expect } from 'vitest';
import { spreadEdgeTies, visibleLabelIds, type LabelCandidate } from '@/components/cockpit/common/radar-labels';

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

  it('caps the number of unpinned labels but never drops a pinned one', () => {
    const input = [node('A-1', 20, 20, 9), node('B-2', 120, 20, 8), node('C-3', 220, 20, 7), node('D-4', 320, 20, 1)];
    const shown = visibleLabelIds(input, new Set(['D-4']), [], 2);
    expect([...shown].sort()).toEqual(['A-1', 'D-4']);
  });

  it('does not mutate its input', () => {
    const input = [node('A-1', 10, 10, 1), node('B-2', 200, 10, 9)];
    visibleLabelIds(input, new Set());
    expect(input.map((c) => c.id)).toEqual(['A-1', 'B-2']);
  });
});

describe('spreadEdgeTies', () => {
  it('leaves values below the edge untouched', () => {
    expect(spreadEdgeTies(0.5, 'PTR-1')).toBe(0.5);
    expect(spreadEdgeTies(0.979, 'PTR-1')).toBe(0.979);
  });

  it('moves edge ties left by at most 5% and never past the edge', () => {
    for (const id of ['PTR-1', 'PTR-22', 'PTR-8809', 'PTR-4819']) {
      const x = spreadEdgeTies(1, id);
      expect(x).toBeLessThanOrEqual(1);
      expect(x).toBeGreaterThan(0.949);
    }
  });

  it('is stable per id and differs across ids', () => {
    expect(spreadEdgeTies(1, 'PTR-9')).toBe(spreadEdgeTies(1, 'PTR-9'));
    const xs = new Set(['PTR-1', 'PTR-2', 'PTR-3', 'PTR-4', 'PTR-5'].map((id) => spreadEdgeTies(1, id)));
    expect(xs.size).toBeGreaterThan(3);
  });
});
