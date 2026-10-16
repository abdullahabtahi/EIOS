import * as React from 'react';
import type { HoverPoint } from './geo-layers';
import type { SelectionView } from './geo-format';

const OFFSET = 14;
const WIDTH = 248;
const MAX_ROWS = 5;

/** A short card beside the pointer: the first facts of what is under it. The full set opens in the panel on click. */
export function GeoTooltip({ view, point, bounds }: { readonly view: SelectionView; readonly point: HoverPoint; readonly bounds: { width: number; height: number } }) {
  const flipX = point.x + OFFSET + WIDTH > bounds.width;
  const flipY = point.y + OFFSET + 140 > bounds.height;
  return (
    <div
      role="tooltip"
      style={{ left: flipX ? point.x - OFFSET - WIDTH : point.x + OFFSET, top: flipY ? point.y - OFFSET - 124 : point.y + OFFSET, width: WIDTH }}
      className="pointer-events-none absolute z-20 border border-cx-line bg-white p-2.5 shadow-md">
      <p className="text-xs font-semibold leading-snug text-cx-ink">{view.title}</p>
      <dl className="mt-1.5 space-y-0.5 text-label">
        {view.rows.slice(0, MAX_ROWS).map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3">
            <dt className="text-cx-muted">{label}</dt>
            <dd className="text-right text-cx-ink">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
