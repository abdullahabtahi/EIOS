/**
 * Where the assistant lives on the geospatial page: not open at all, a window floating over the map, or docked as a
 * column at the left. The geometry is pure so it can be tested; what is remembered is only the choice between
 * floating and docked and where the window was left, never the conversation.
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

/** The window's size on a map of this size: full size when there is room, otherwise what fits inside the margins. */
export function windowSize(bounds: Box): Box {
  return {
    width: Math.max(0, Math.min(CHAT_SIZE.width, bounds.width - 2 * CHAT_MARGIN)),
    height: Math.max(0, Math.min(CHAT_SIZE.height, bounds.height - 2 * CHAT_MARGIN)),
  };
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
  readonly open: OpenMode;
  readonly pos: Point | null;
}
export interface DockStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export const DOCK_KEY = 'eios.geo.chat';
const FIRST: DockPrefs = { open: 'floating', pos: null };

const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);

/** What was remembered, checked field by field: a stored value that is not trusted is dropped, not repaired. */
export function loadPrefs(storage: DockStorage | null = browserStorage()): DockPrefs {
  try {
    const raw = storage?.getItem(DOCK_KEY);
    if (!raw) return FIRST;
    const parsed = JSON.parse(raw) as { open?: unknown; pos?: { x?: unknown; y?: unknown } | null };
    const open: OpenMode = parsed.open === 'docked' ? 'docked' : 'floating';
    const pos = parsed.pos && finite(parsed.pos.x) && finite(parsed.pos.y) ? { x: parsed.pos.x, y: parsed.pos.y } : null;
    return { open, pos };
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
