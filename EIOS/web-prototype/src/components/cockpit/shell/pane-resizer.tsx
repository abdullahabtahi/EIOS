'use client';

/**
 * Accessible vertical splitter (WAI-ARIA window splitter pattern).
 * Drag with the pointer, or focus and use Arrow keys (Shift = coarse step),
 * Home / End for the bounds, Enter or double-click to restore the default.
 */

import * as React from 'react';
import { clampWidth } from './use-persisted-width';

const STEP = 16;
const COARSE_STEP = 80;

export interface PaneResizerProps {
  readonly label: string;
  readonly value: number;
  readonly min: number;
  readonly max: number;
  readonly defaultValue: number;
  readonly onChange: (next: number) => void;
  /** Set when the controlled pane sits to the right of the handle (dragging left grows it). */
  readonly invert?: boolean;
}

export function PaneResizer({ label, value, min, max, defaultValue, onChange, invert = false }: PaneResizerProps) {
  const [dragging, setDragging] = React.useState(false);
  const start = React.useRef({ x: 0, value: 0 });
  const onChangeRef = React.useRef(onChange);
  React.useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  React.useEffect(() => {
    if (!dragging) return;
    const dir = invert ? -1 : 1;
    const onMove = (e: PointerEvent) => {
      onChangeRef.current(clampWidth(start.current.value + (e.clientX - start.current.x) * dir, min, max));
    };
    const stop = () => setDragging(false);
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
    document.body.style.cursor = 'col-resize';
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
      document.body.style.cursor = '';
    };
  }, [dragging, invert, min, max]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const step = e.shiftKey ? COARSE_STEP : STEP;
    const grow = invert ? 'ArrowLeft' : 'ArrowRight';
    const shrink = invert ? 'ArrowRight' : 'ArrowLeft';
    if (e.key === grow) onChange(clampWidth(value + step, min, max));
    else if (e.key === shrink) onChange(clampWidth(value - step, min, max));
    else if (e.key === 'Home') onChange(min);
    else if (e.key === 'End') onChange(max);
    else if (e.key === 'Enter') onChange(defaultValue);
    else return;
    e.preventDefault();
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuenow={value}
      aria-valuemin={min}
      aria-valuemax={max}
      tabIndex={0}
      title="Drag to resize · double-click to reset"
      onKeyDown={handleKeyDown}
      onDoubleClick={() => onChange(defaultValue)}
      onPointerDown={(e) => {
        e.preventDefault();
        start.current = { x: e.clientX, value };
        setDragging(true);
      }}
      className={`group relative z-10 w-px shrink-0 cursor-col-resize touch-none outline-none transition-colors ${
        dragging ? 'bg-cx-accent' : 'bg-slate-200 hover:bg-cx-accent focus-visible:bg-cx-accent'
      }`}
    >
      {/* Generous invisible hit area around the 1px line */}
      <span className="absolute inset-y-0 -left-1.5 -right-1.5" />
    </div>
  );
}
