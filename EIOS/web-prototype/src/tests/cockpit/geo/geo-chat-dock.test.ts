import { describe, it, expect } from 'vitest';
import { CHAT_MARGIN, CHAT_SIZE, clampPosition, defaultPosition, loadPrefs, nudge, savePrefs, windowSize, type DockStorage } from '@/components/cockpit/geo/geo-chat-dock';

const BOUNDS = { width: 1000, height: 700 };
const memory = (initial: Record<string, string> = {}): DockStorage & { data: Record<string, string> } => {
  const data = { ...initial };
  return { data, getItem: (k) => data[k] ?? null, setItem: (k, v) => void (data[k] = v) };
};

describe('the chat window geometry', () => {
  it('is its full size on a roomy map and shrinks to fit a small one, leaving a margin', () => {
    expect(windowSize(BOUNDS)).toEqual(CHAT_SIZE);
    const small = windowSize({ width: 300, height: 400 });
    expect(small.width).toBe(300 - 2 * CHAT_MARGIN);
    expect(small.height).toBe(400 - 2 * CHAT_MARGIN);
  });

  it('keeps the window wholly inside the map, whatever it is dragged to', () => {
    const size = windowSize(BOUNDS);
    expect(clampPosition({ x: -500, y: -500 }, size, BOUNDS)).toEqual({ x: CHAT_MARGIN, y: CHAT_MARGIN });
    expect(clampPosition({ x: 5000, y: 5000 }, size, BOUNDS)).toEqual({
      x: BOUNDS.width - size.width - CHAT_MARGIN,
      y: BOUNDS.height - size.height - CHAT_MARGIN,
    });
    expect(clampPosition({ x: 200, y: 100 }, size, BOUNDS)).toEqual({ x: 200, y: 100 });
  });

  it('starts at the bottom right, where the launcher is', () => {
    const size = windowSize(BOUNDS);
    expect(defaultPosition(size, BOUNDS)).toEqual({ x: BOUNDS.width - size.width - CHAT_MARGIN, y: BOUNDS.height - size.height - CHAT_MARGIN });
  });

  it('does not return a negative position for a map smaller than the margins', () => {
    const p = clampPosition({ x: 10, y: 10 }, { width: 100, height: 100 }, { width: 50, height: 50 });
    expect(p.x).toBeGreaterThanOrEqual(0);
    expect(p.y).toBeGreaterThanOrEqual(0);
  });

  it('moves by a step with the arrow keys, further with Shift, and ignores other keys', () => {
    expect(nudge({ x: 100, y: 100 }, 'ArrowLeft', false)).toEqual({ x: 90, y: 100 });
    expect(nudge({ x: 100, y: 100 }, 'ArrowDown', true)).toEqual({ x: 100, y: 150 });
    expect(nudge({ x: 100, y: 100 }, 'Enter', false)).toBeNull();
  });
});

describe('what the chat remembers', () => {
  it('opens floating, with no position, the first time', () => {
    expect(loadPrefs(memory())).toEqual({ open: 'floating', pos: null });
  });

  it('remembers whether it was docked and where the window was left', () => {
    const store = memory();
    savePrefs({ open: 'docked', pos: { x: 12, y: 34 } }, store);
    expect(loadPrefs(store)).toEqual({ open: 'docked', pos: { x: 12, y: 34 } });
  });

  it('ignores anything it cannot trust: bad JSON, an unknown mode, a position that is not numbers', () => {
    expect(loadPrefs(memory({ 'eios.geo.chat': '{nope' }))).toEqual({ open: 'floating', pos: null });
    expect(loadPrefs(memory({ 'eios.geo.chat': JSON.stringify({ open: 'sideways', pos: { x: 'a', y: 1 } }) }))).toEqual({ open: 'floating', pos: null });
    expect(loadPrefs(memory({ 'eios.geo.chat': JSON.stringify({ open: 'docked', pos: { x: NaN, y: 1 } }) }))).toEqual({ open: 'docked', pos: null });
  });

  it('works without storage, and when storage throws', () => {
    const broken: DockStorage = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
    expect(loadPrefs(broken)).toEqual({ open: 'floating', pos: null });
    expect(() => savePrefs({ open: 'docked', pos: null }, broken)).not.toThrow();
    expect(loadPrefs(null)).toEqual({ open: 'floating', pos: null });
  });
});
