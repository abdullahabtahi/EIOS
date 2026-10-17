import { describe, it, expect } from 'vitest';
import { declutterLabels, type PlacedLabel } from '@/components/cockpit/geo/geo-labels';

const label = (name: string, lng: number, lat: number, priority: number): PlacedLabel => ({ name, position: [lng, lat], priority });
const names = (rows: readonly PlacedLabel[]) => rows.map((r) => r.name).sort();

describe('keeping map labels readable', () => {
  it('keeps both names when they are far apart', () => {
    expect(names(declutterLabels([label('Nigeria', 8, 9, 1), label('Vietnam', 106, 16, 1)], 2))).toEqual(['Nigeria', 'Vietnam']);
  });

  it('drops the smaller name when two would print over each other', () => {
    const rows = [label('Singapore', 103.8, 1.35, 10), label('Malaysia', 102, 3, 50), label('Indonesia', 104, 0.5, 30)];
    expect(names(declutterLabels(rows, 2))).toEqual(['Malaysia']);
  });

  it('brings the hidden names back as the map zooms in and makes room', () => {
    const rows = [label('Singapore', 103.8, 1.35, 10), label('Malaysia', 102, 3, 50), label('Indonesia', 104, 0.5, 30)];
    expect(names(declutterLabels(rows, 6)).length).toBe(3);
  });

  it('keeps the highest priority whatever order the rows come in', () => {
    const a = [label('Small', 100, 2, 1), label('Big', 101, 2, 9)];
    expect(names(declutterLabels(a, 2))).toEqual(['Big']);
    expect(names(declutterLabels([...a].reverse(), 2))).toEqual(['Big']);
  });

  it('returns nothing for nothing, and never mutates its input', () => {
    expect(declutterLabels([], 2)).toEqual([]);
    const rows = [label('A', 0, 0, 1), label('B', 0.1, 0, 2)];
    const copy = JSON.stringify(rows);
    declutterLabels(rows, 2);
    expect(JSON.stringify(rows)).toBe(copy);
  });
});
