'use client';

import * as React from 'react';
import { type Box, type DockMode, type DockPrefs, loadPrefs, type OpenMode, type Point, savePrefs } from './geo-chat-dock';

export interface ChatDock {
  readonly mode: DockMode;
  readonly pos: Point | null;
  /** The size the analyst resized the window to, or null for the default. */
  readonly size: Box | null;
  readonly show: () => void;
  readonly close: () => void;
  readonly dock: () => void;
  readonly float: () => void;
  /** The window is being dragged: follow it, remember nothing yet. */
  readonly move: (pos: Point) => void;
  /** The window was let go or nudged: remember where it is. */
  readonly settle: (pos: Point) => void;
  /** The corner is being dragged: follow the new size and position, remember nothing yet. */
  readonly resizeTo: (size: Box, pos: Point) => void;
  /** The corner was let go, nudged or reset (null, null): remember the size and position. */
  readonly settleResize: (size: Box | null, pos: Point | null) => void;
}

/**
 * Where the assistant is: closed, floating or docked. It always starts closed, as a launcher; the choice between floating and
 * docked and the window's position are remembered in this browser.
 */
export function useChatDock(): ChatDock {
  // Read on the first render. The window is closed then, and closed looks the same whatever was remembered, so the
  // server's markup and the browser's first render agree; what was remembered only shows once it is opened.
  const [prefs] = React.useState<DockPrefs>(() => loadPrefs());
  const [open, setOpen] = React.useState(false);
  const [way, setWay] = React.useState<OpenMode>(prefs.open);
  const [pos, setPos] = React.useState<Point | null>(prefs.pos);
  const [size, setSize] = React.useState<Box | null>(prefs.size);
  // What is remembered is read from a ref, so the actions below stay the same functions from one render to the next.
  const current = React.useRef<DockPrefs>(prefs);

  const remember = React.useCallback((next: DockPrefs) => {
    current.current = next;
    savePrefs(next);
  }, []);
  const show = React.useCallback(() => setOpen(true), []);
  const close = React.useCallback(() => setOpen(false), []);
  const dock = React.useCallback(() => {
    setWay('docked');
    remember({ ...current.current, open: 'docked' });
  }, [remember]);
  const float = React.useCallback(() => {
    setWay('floating');
    remember({ ...current.current, open: 'floating' });
  }, [remember]);
  const settle = React.useCallback(
    (p: Point) => {
      setPos(p);
      remember({ ...current.current, pos: p });
    },
    [remember],
  );

  const resizeTo = React.useCallback((next: Box, at: Point) => {
    setSize(next);
    setPos(at);
  }, []);
  const settleResize = React.useCallback(
    (next: Box | null, at: Point | null) => {
      setSize(next);
      setPos(at);
      remember({ ...current.current, size: next, pos: at });
    },
    [remember],
  );

  return { mode: open ? way : 'closed', pos, size, show, close, dock, float, move: setPos, settle, resizeTo, settleResize };
}
