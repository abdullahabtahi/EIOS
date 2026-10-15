import * as React from 'react';
import { MAX_MISMATCH_PAIRS } from './geo-layers';

const ITEMS: readonly { readonly swatch: string; readonly label: string }[] = [
  { swatch: 'bg-cx-bad/30 border border-cx-bad', label: 'FATF call for action' },
  { swatch: 'bg-cx-warn/30 border border-cx-warn', label: 'FATF increased monitoring' },
  { swatch: 'bg-cx-accent/60 rounded-full', label: 'Offshore entities (size = count)' },
  { swatch: 'bg-cx-ink-soft h-0.5 self-center', label: 'IP ≠ KYC country' },
  { swatch: 'bg-cx-warn h-0.5 self-center', label: 'Corridor, colour = risk tier' },
];

/** What the marks on the map mean; every colour here is the one the layers use. */
export function GeoLegend() {
  return (
    <ul aria-label="Map legend" className="w-60 space-y-1 border border-cx-line bg-white/95 p-2 text-label text-cx-ink-soft shadow-md">
      {ITEMS.map((item) => (
        <li key={item.label} className="flex items-center gap-2">
          <span aria-hidden="true" className={`inline-block w-4 shrink-0 ${item.swatch.includes('h-0.5') ? '' : 'h-3'} ${item.swatch}`} />
          {item.label}
        </li>
      ))}
      <li className="border-t border-cx-line-soft pt-1 text-cx-muted">
        Arcs: all elevated corridors, the largest others, and the {MAX_MISMATCH_PAIRS} largest flagged pairs.
      </li>
    </ul>
  );
}
