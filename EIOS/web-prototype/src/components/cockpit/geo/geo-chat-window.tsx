'use client';

import * as React from 'react';
import { Icon } from '@/components/ui/icon';
import { type Box, clampPosition, defaultPosition, type DockMode, nudge, type Point, windowSize } from './geo-chat-dock';

export interface GeoChatWindowProps {
  readonly mode: DockMode;
  readonly pos: Point | null;
  /** The map's size: the window floats inside it and never leaves it. */
  readonly bounds: Box;
  readonly onMove: (pos: Point) => void;
  readonly onSettle: (pos: Point) => void;
  readonly onDock: () => void;
  readonly onFloat: () => void;
  readonly onClose: () => void;
  readonly children: React.ReactNode;
}

interface Drag {
  readonly from: Point;
  readonly at: Point;
}

const BUTTON = 'flex size-7 shrink-0 cursor-pointer items-center justify-center text-cx-muted outline-none hover:bg-cx-sub-2 hover:text-cx-ink focus-visible:ring-2 focus-visible:ring-cx-accent';

/**
 * The assistant's frame. One element for all three states so the conversation inside is never unmounted: closed (kept but
 * not shown), floating over the map (moved by its handle, with the pointer or the arrow keys), or docked as the first
 * column of the page. Its content is the caller's.
 */
export function GeoChatWindow({ mode, pos, bounds, onMove, onSettle, onDock, onFloat, onClose, children }: GeoChatWindowProps) {
  const floating = mode === 'floating';
  const size = windowSize(bounds);
  const at = clampPosition(pos ?? defaultPosition(size, bounds), size, bounds);
  const drag = React.useRef<Drag | null>(null);

  const style: React.CSSProperties =
    mode === 'closed' ? { display: 'none' } : floating ? { left: at.x, top: at.y, width: size.width, height: size.height } : {};

  return (
    <div
      data-testid="geo-chat"
      data-mode={mode}
      style={style}
      className={
        floating
          ? 'geo-chat-in absolute z-30 flex flex-col overflow-hidden bg-white shadow-xl'
          : 'geo-chat-in z-30 flex min-h-0 flex-col bg-white max-lg:absolute max-lg:inset-x-2 max-lg:bottom-2 max-lg:top-16 max-lg:shadow-xl lg:relative lg:w-[24rem] lg:shrink-0 lg:border-r lg:border-cx-line'
      }>
      <header className="flex shrink-0 items-center gap-1 bg-white pl-2 pr-2">
        {floating ? (
          <button
            type="button"
            aria-label="Move chat window"
            title="Drag to move, or use the arrow keys"
            onPointerDown={(e) => {
              if (e.button !== 0) return;
              drag.current = { from: { x: e.clientX, y: e.clientY }, at };
              e.currentTarget.setPointerCapture?.(e.pointerId);
            }}
            onPointerMove={(e) => {
              const d = drag.current;
              if (d) onMove(clampPosition({ x: d.at.x + e.clientX - d.from.x, y: d.at.y + e.clientY - d.from.y }, size, bounds));
            }}
            onPointerUp={(e) => {
              const d = drag.current;
              drag.current = null;
              if (d) onSettle(clampPosition({ x: d.at.x + e.clientX - d.from.x, y: d.at.y + e.clientY - d.from.y }, size, bounds));
            }}
            onKeyDown={(e) => {
              const next = nudge(at, e.key, e.shiftKey);
              if (!next) return;
              e.preventDefault();
              onSettle(clampPosition(next, size, bounds));
            }}
            className="flex min-w-0 flex-1 cursor-grab touch-none items-center gap-1.5 px-2 py-3 text-left text-sm font-semibold text-cx-ink outline-none focus-visible:ring-2 focus-visible:ring-cx-accent active:cursor-grabbing">
            <Icon icon="drag_indicator" size="sm" className="text-cx-faint" />
            Ask
          </button>
        ) : (
          <h2 className="flex min-w-0 flex-1 items-center gap-1.5 px-2 py-3 text-sm font-semibold text-cx-ink">
            <Icon icon="auto_awesome" size="sm" className="text-cx-accent" />
            Ask
          </h2>
        )}
        <button
          type="button"
          aria-label={floating ? 'Dock chat to the left' : 'Float chat over the map'}
          title={floating ? 'Dock to the left' : 'Float over the map'}
          onClick={floating ? onDock : onFloat}
          className={BUTTON}>
          <Icon icon={floating ? 'dock_to_left' : 'picture_in_picture'} size="sm" />
        </button>
        <button type="button" aria-label="Close chat" title="Close" onClick={onClose} className={BUTTON}>
          <Icon icon="close" size="sm" />
        </button>
      </header>
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
