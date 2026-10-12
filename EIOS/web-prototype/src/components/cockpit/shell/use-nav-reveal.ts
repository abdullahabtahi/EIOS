'use client';

/**
 * Hover-intent reveal controller for the auto-hiding global navigation rail.
 * - Opens after a short hover intent (so grazing the edge does nothing).
 * - Closes after a grace period (so a wobbly pointer path does not dismiss it).
 * - Keyboard focus, `\` toggle and touch use the immediate `open` / `toggle` paths.
 */

import * as React from 'react';

export const NAV_OPEN_INTENT_MS = 120;
export const NAV_CLOSE_GRACE_MS = 280;

export interface NavReveal {
  readonly open: boolean;
  readonly openNow: () => void;
  readonly closeNow: () => void;
  readonly toggle: () => void;
  readonly scheduleOpen: () => void;
  readonly scheduleClose: () => void;
  readonly cancelScheduled: () => void;
}

export function useNavReveal(): NavReveal {
  const [open, setOpen] = React.useState(false);
  const timer = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelScheduled = React.useCallback(() => {
    if (timer.current !== null) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  }, []);

  const openNow = React.useCallback(() => {
    cancelScheduled();
    setOpen(true);
  }, [cancelScheduled]);

  const closeNow = React.useCallback(() => {
    cancelScheduled();
    setOpen(false);
  }, [cancelScheduled]);

  const toggle = React.useCallback(() => {
    cancelScheduled();
    setOpen((prev) => !prev);
  }, [cancelScheduled]);

  const scheduleOpen = React.useCallback(() => {
    cancelScheduled();
    timer.current = setTimeout(() => {
      timer.current = null;
      setOpen(true);
    }, NAV_OPEN_INTENT_MS);
  }, [cancelScheduled]);

  const scheduleClose = React.useCallback(() => {
    cancelScheduled();
    timer.current = setTimeout(() => {
      timer.current = null;
      setOpen(false);
    }, NAV_CLOSE_GRACE_MS);
  }, [cancelScheduled]);

  React.useEffect(() => cancelScheduled, [cancelScheduled]);

  return { open, openNow, closeNow, toggle, scheduleOpen, scheduleClose, cancelScheduled };
}
