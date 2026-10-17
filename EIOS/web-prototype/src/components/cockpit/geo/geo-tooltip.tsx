import * as React from 'react';
import type { HoverPoint } from './geo-layers';
import type { SelectionView } from './geo-format';
import { placeTooltip } from './geo-tooltip-place';

const WIDTH = 248;
const MAX_ROWS = 5;

/** A short card beside the pointer: the first facts of what is under it. The full set opens in the panel on click. */
export function GeoTooltip({ view, point, bounds }: { readonly view: SelectionView; readonly point: HoverPoint; readonly bounds: { width: number; height: number } }) {
  const card = React.useRef<HTMLDivElement>(null);
  // The card's own height, measured before it is painted: its rows and a wrapped title change it, so a fixed guess flips too early or too late.
  const [height, setHeight] = React.useState(0);
  React.useLayoutEffect(() => {
    if (card.current) setHeight(card.current.offsetHeight);
  }, [view]);
  const { left, top } = placeTooltip(point, { width: WIDTH, height }, bounds);
  return (
    <div
      ref={card}
      role="tooltip"
      style={{ left, top, width: WIDTH }}
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
