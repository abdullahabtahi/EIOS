/**
 * Where the assistant lives on the geospatial page: not open at all, a window floating over the map, or docked as a
 * column at the left. The geometry is pure so it can be tested; what is remembered is only where the window was left
 * and how big it was made, never the conversation and never the choice of docking: every launch is the floating window.
 */

export type DockMode = 'closed' | 'floating' | 'docked';
export type OpenMode = Exclude<DockMode, 'closed'>;

export interface Point {
  readonly x: number;
  readonly y: number;
}
export interface Box {
  readonly width: number;
  readonly height: number;
}

/** [ASSUMPTION] the window's size in pixels, wide enough for a table of figures and short enough to leave the map in view. */
export const CHAT_SIZE: Box = { width: 352, height: 512 };
export const CHAT_MARGIN = 12;
const STEP = 10;
const BIG_STEP = 50;

/** [ASSUMPTION] the smallest the window can be made: a question box and a few lines of answer. */
export const MIN_CHAT_SIZE: Box = { width: 280, height: 320 };
const MAX_REMEMBERED = 4000;

/** The window's size on a map of this size: the size asked for (the default, or what was remembered) when there is room, otherwise what fits inside the margins. */
export function windowSize(bounds: Box, preferred: Box = CHAT_SIZE): Box {
  return {
    width: Math.max(0, Math.min(preferred.width, bounds.width - 2 * CHAT_MARGIN)),
    height: Math.max(0, Math.min(preferred.height, bounds.height - 2 * CHAT_MARGIN)),
  };
}

/** A size held between the minimum and the map's far edge, a margin from it, for a window whose top left is at `at`. */
function clampSize(size: Box, at: Point, bounds: Box): Box {
  const fit = (n: number, min: number, start: number, limit: number) => Math.max(Math.min(min, limit - 2 * CHAT_MARGIN), Math.min(n, limit - start - CHAT_MARGIN));
  return { width: fit(size.width, MIN_CHAT_SIZE.width, at.x, bounds.width), height: fit(size.height, MIN_CHAT_SIZE.height, at.y, bounds.height) };
}

/** The size after the corner is dragged by (dx, dy). */
export function resizedSize(from: Box, dx: number, dy: number, at: Point, bounds: Box): Box {
  return clampSize({ width: from.width + dx, height: from.height + dy }, at, bounds);
}

/**
 * Resizes from the top left corner, dragged by (dx, dy), with the bottom right held where it is: the window starts at the
 * bottom right of the map, where the only way to grow is up and to the left. Returns the new size and top left.
 */
export function cornerResize(size: Box, at: Point, dx: number, dy: number, bounds: Box): { size: Box; pos: Point } {
  const anchor = { x: at.x + size.width, y: at.y + size.height };
  // Mirror the map so "room to grow" is the room left of the anchor, and reuse the one clamp.
  const next = resizedSize(size, -dx, -dy, { x: bounds.width - anchor.x, y: bounds.height - anchor.y }, bounds);
  return { size: next, pos: { x: anchor.x - next.width, y: anchor.y - next.height } };
}

/** Keeps the whole window inside the map, a margin from every edge. */
export function clampPosition(pos: Point, size: Box, bounds: Box): Point {
  const maxX = Math.max(CHAT_MARGIN, bounds.width - size.width - CHAT_MARGIN);
  const maxY = Math.max(CHAT_MARGIN, bounds.height - size.height - CHAT_MARGIN);
  return { x: Math.min(Math.max(pos.x, CHAT_MARGIN), maxX), y: Math.min(Math.max(pos.y, CHAT_MARGIN), maxY) };
}

/** Where the window first appears: the bottom right, beside the launcher it came from. */
export const defaultPosition = (size: Box, bounds: Box): Point => clampPosition({ x: Infinity, y: Infinity }, size, bounds);

const ARROW: Readonly<Record<string, readonly [number, number]>> = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };

/** The position after an arrow key, further with Shift; null for any other key. */
export function nudge(pos: Point, key: string, big: boolean): Point | null {
  const dir = ARROW[key];
  if (!dir) return null;
  const step = big ? BIG_STEP : STEP;
  return { x: pos.x + dir[0] * step, y: pos.y + dir[1] * step };
}

export interface DockPrefs {
  readonly pos: Point | null;
  /** The size the analyst dragged the window to; null until they do. */
  readonly size: Box | null;
}
export interface DockStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export const DOCK_KEY = 'eios.geo.chat';
const FIRST: DockPrefs = { pos: null, size: null };

const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);

/** What was remembered, checked field by field: a stored value that is not trusted is dropped, not repaired. */
export function loadPrefs(storage: DockStorage | null = browserStorage()): DockPrefs {
  try {
    const raw = storage?.getItem(DOCK_KEY);
    if (!raw) return FIRST;
    const parsed = JSON.parse(raw) as { pos?: { x?: unknown; y?: unknown } | null; size?: { width?: unknown; height?: unknown } | null };
    const pos = parsed.pos && finite(parsed.pos.x) && finite(parsed.pos.y) ? { x: parsed.pos.x, y: parsed.pos.y } : null;
    const sized = (n: unknown, min: number): n is number => finite(n) && n >= min && n <= MAX_REMEMBERED;
    const size = parsed.size && sized(parsed.size.width, MIN_CHAT_SIZE.width) && sized(parsed.size.height, MIN_CHAT_SIZE.height) ? { width: parsed.size.width, height: parsed.size.height } : null;
    return { pos, size };
  } catch {
    return FIRST;
  }
}

/** Remembers the choice. Storage can be blocked or full; the page works without it, so a failure is not an error. */
export function savePrefs(prefs: DockPrefs, storage: DockStorage | null = browserStorage()): void {
  try {
    storage?.setItem(DOCK_KEY, JSON.stringify(prefs));
  } catch {
    // Private windows and blocked storage: the chat simply opens in its default place next time.
  }
}

function browserStorage(): DockStorage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}
