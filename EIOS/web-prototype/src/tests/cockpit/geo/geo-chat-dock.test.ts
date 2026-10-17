import { describe, it, expect } from 'vitest';
import { CHAT_MARGIN, CHAT_SIZE, clampPosition, defaultPosition, loadPrefs, MIN_CHAT_SIZE, cornerResize, nudge, resizedSize, savePrefs, windowSize, type DockStorage } from '@/components/cockpit/geo/geo-chat-dock';

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
  it('has no position or size the first time', () => {
    expect(loadPrefs(memory())).toEqual({ pos: null, size: null });
  });

  it('remembers where the window was left and how big it was made', () => {
    const store = memory();
    savePrefs({ pos: { x: 12, y: 34 }, size: { width: 400, height: 500 } }, store);
    expect(loadPrefs(store)).toEqual({ pos: { x: 12, y: 34 }, size: { width: 400, height: 500 } });
  });

  it('ignores anything it cannot trust: bad JSON, a position that is not numbers, an old docked choice', () => {
    expect(loadPrefs(memory({ 'eios.geo.chat': '{nope' }))).toEqual({ pos: null, size: null });
    expect(loadPrefs(memory({ 'eios.geo.chat': JSON.stringify({ open: 'docked', pos: { x: 'a', y: 1 } }) }))).toEqual({ pos: null, size: null });
    expect(loadPrefs(memory({ 'eios.geo.chat': JSON.stringify({ open: 'docked', pos: { x: NaN, y: 1 } }) }))).toEqual({ pos: null, size: null });
  });

  it('works without storage, and when storage throws', () => {
    const broken: DockStorage = { getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); } };
    expect(loadPrefs(broken)).toEqual({ pos: null, size: null });
    expect(() => savePrefs({ pos: null, size: null }, broken)).not.toThrow();
    expect(loadPrefs(null)).toEqual({ pos: null, size: null });
  });
});

describe('resizing the chat window', () => {
  const at = { x: 100, y: 80 };

  it('uses the remembered size when there is room, and still fits a small map', () => {
    expect(windowSize(BOUNDS, { width: 420, height: 560 })).toEqual({ width: 420, height: 560 });
    expect(windowSize({ width: 300, height: 400 }, { width: 420, height: 560 })).toEqual({ width: 300 - 2 * CHAT_MARGIN, height: 400 - 2 * CHAT_MARGIN });
  });

  it('grows and shrinks with the pointer, never below the minimum', () => {
    expect(resizedSize(CHAT_SIZE, 40, 30, at, BOUNDS)).toEqual({ width: CHAT_SIZE.width + 40, height: CHAT_SIZE.height + 30 });
    expect(resizedSize(CHAT_SIZE, -900, -900, at, BOUNDS)).toEqual(MIN_CHAT_SIZE);
  });

  it('never grows past the map edge, a margin from it', () => {
    const size = resizedSize(CHAT_SIZE, 5000, 5000, at, BOUNDS);
    expect(at.x + size.width).toBe(BOUNDS.width - CHAT_MARGIN);
    expect(at.y + size.height).toBe(BOUNDS.height - CHAT_MARGIN);
  });

  it('resizes from the top left corner with the bottom right held still, so a window at the bottom right can grow', () => {
    const size = windowSize(BOUNDS);
    const at = defaultPosition(size, BOUNDS);
    const grown = cornerResize(size, at, -60, -40, BOUNDS);
    expect(grown.size).toEqual({ width: size.width + 60, height: size.height + 40 });
    expect(grown.pos.x + grown.size.width).toBe(at.x + size.width);
    expect(grown.pos.y + grown.size.height).toBe(at.y + size.height);
  });

  it('stops growing at the map edge and shrinking at the minimum, still anchored', () => {
    const size = windowSize(BOUNDS);
    const at = defaultPosition(size, BOUNDS);
    const huge = cornerResize(size, at, -5000, -5000, BOUNDS);
    expect(huge.pos).toEqual({ x: CHAT_MARGIN, y: CHAT_MARGIN });
    const tiny = cornerResize(size, at, 5000, 5000, BOUNDS);
    expect(tiny.size).toEqual(MIN_CHAT_SIZE);
    expect(tiny.pos.x + tiny.size.width).toBe(at.x + size.width);
  });

  it('drops a remembered size that is not numbers or is out of range', () => {
    const bad = (size: unknown) => loadPrefs(memory({ 'eios.geo.chat': JSON.stringify({ size }) })).size;
    expect(bad({ width: 'a', height: 400 })).toBeNull();
    expect(bad({ width: 10, height: 10 })).toBeNull();
    expect(bad({ width: 99999, height: 400 })).toBeNull();
    expect(bad({ width: 400, height: 500 })).toEqual({ width: 400, height: 500 });
  });
});
