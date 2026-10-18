'use client';

import * as React from 'react';
import { Icon } from '@/components/ui/icon';
import { ASSISTANT_ICON } from './geo-chat-launcher';
import { type Box, clampPosition, cornerResize, defaultPosition, type DockMode, nudge, type Point, windowSize } from './geo-chat-dock';

export interface GeoChatWindowProps {
  readonly mode: DockMode;
  readonly pos: Point | null;
  /** The size the analyst resized it to; null for the default. */
  readonly size: Box | null;
  /** The map's size: the window floats inside it and never leaves it. */
  readonly bounds: Box;
  readonly onMove: (pos: Point) => void;
  readonly onSettle: (pos: Point) => void;
  /** The top left corner is being dragged: follow it (new size and position), remember nothing yet. */
  readonly onResize: (size: Box, pos: Point) => void;
  /** The corner was let go, nudged or reset: remember the size (null puts it back to the default) and the position. */
  readonly onResizeSettle: (size: Box | null, pos: Point | null) => void;
  readonly onDock: () => void;
  readonly onFloat: () => void;
  readonly onClose: () => void;
  /** Starts a new conversation; absent while there is nothing to clear or an answer is on its way. */
  readonly onNewChat?: () => void;
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
export function GeoChatWindow({ mode, pos, size: remembered, bounds, onMove, onSettle, onResize, onResizeSettle, onDock, onFloat, onClose, onNewChat, children }: GeoChatWindowProps) {
  const floating = mode === 'floating';
  const size = windowSize(bounds, remembered ?? undefined);
  const at = clampPosition(pos ?? defaultPosition(size, bounds), size, bounds);
  const drag = React.useRef<Drag | null>(null);
  const grab = React.useRef<{ from: Point; size: Box; at: Point } | null>(null);

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
      <header className="flex shrink-0 items-center gap-1 border-b border-cx-line-soft bg-white pl-1.5 pr-1.5">
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
            className="flex min-w-0 flex-1 cursor-grab touch-none items-center gap-2 px-2.5 py-3 text-left text-sm font-semibold text-cx-ink outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent active:cursor-grabbing">
            <Icon icon="drag_indicator" size="sm" className="shrink-0 text-cx-muted" />
            <span className="truncate">Geospatial Agent</span>
          </button>
        ) : (
          <h2 className="flex min-w-0 flex-1 items-center gap-2 px-2.5 py-3 text-sm font-semibold text-cx-ink">
            <Icon icon={ASSISTANT_ICON} size="sm" className="text-cx-accent" />
            <span className="truncate">Geospatial Agent</span>
          </h2>
        )}
        {onNewChat && (
          <button type="button" aria-label="New chat" title="New chat" onClick={onNewChat} className={BUTTON}>
            <Icon icon="edit_square" size="sm" />
          </button>
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
      {floating && (
        <button
          type="button"
          aria-label="Resize chat window"
          title="Drag to resize, arrow keys to resize, double-click to reset"
          onPointerDown={(e) => {
            if (e.button !== 0) return;
            grab.current = { from: { x: e.clientX, y: e.clientY }, size, at };
            e.currentTarget.setPointerCapture?.(e.pointerId);
          }}
          onPointerMove={(e) => {
            const g = grab.current;
            if (!g) return;
            const next = cornerResize(g.size, g.at, e.clientX - g.from.x, e.clientY - g.from.y, bounds);
            onResize(next.size, next.pos);
          }}
          onPointerUp={(e) => {
            const g = grab.current;
            grab.current = null;
            if (!g) return;
            const next = cornerResize(g.size, g.at, e.clientX - g.from.x, e.clientY - g.from.y, bounds);
            onResizeSettle(next.size, next.pos);
          }}
          onKeyDown={(e) => {
            const delta = nudge({ x: 0, y: 0 }, e.key, e.shiftKey);
            if (!delta) return;
            e.preventDefault();
            // Left and up move the corner outward, so they grow the window; right and down shrink it.
            const next = cornerResize(size, at, delta.x, delta.y, bounds);
            onResizeSettle(next.size, next.pos);
          }}
          onDoubleClick={() => onResizeSettle(null, null)}
          className="group absolute left-0 top-0 z-10 size-4 cursor-nwse-resize touch-none outline-none">
          {/* No glyph at rest: the corner is a hit area, and a small bracket shows it on hover and focus. */}
          <span aria-hidden="true" className="absolute left-0.5 top-0.5 size-2 border-l-2 border-t-2 border-cx-accent opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 motion-reduce:transition-none" />
        </button>
      )}
    </div>
  );
}
