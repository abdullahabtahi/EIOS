import * as React from 'react';
import { drawnKinds, rankedCorridors, rankedPairs, shownCorridors, shownPairs } from './geo-rank';
import type { GeoFlows, LayerId } from './geo-types';

interface Key {
  readonly layer: LayerId;
  /** For corridor keys: the kind of arc, so a colour that is not on the map is not in the legend. */
  readonly kind?: 'high' | 'medium' | 'other';
  readonly swatch: string;
  readonly label: string;
}

const KEYS: readonly Key[] = [
  { layer: 'risk', swatch: 'h-3 bg-cx-bad/30 border border-cx-bad', label: 'FATF call for action' },
  { layer: 'risk', swatch: 'h-3 bg-cx-warn/30 border border-cx-warn', label: 'FATF increased monitoring' },
  { layer: 'offshore', swatch: 'h-3 bg-cx-accent/60 rounded-full', label: 'Offshore entities (size = count)' },
  { layer: 'corridors', kind: 'high', swatch: 'h-0.5 bg-cx-bad', label: 'High-risk corridor' },
  { layer: 'corridors', kind: 'medium', swatch: 'h-0.5 bg-cx-warn-solid', label: 'Medium-risk corridor' },
  { layer: 'corridors', kind: 'other', swatch: 'h-0.5 bg-cx-faint', label: 'Other corridor' },
  { layer: 'mismatches', swatch: 'h-0.5 bg-cx-accent', label: 'Registered here, logging in there' },
];

/** What is drawn but not all of what exists: the counts come from the same ranking the layers use. */
export function drawnCounts(flows: GeoFlows | null, visible: ReadonlySet<LayerId>): readonly string[] {
  if (!flows) return [];
  const notes: string[] = [];
  if (visible.has('corridors')) notes.push(`${shownCorridors(flows).length} of ${rankedCorridors(flows).length} corridors`);
  if (visible.has('mismatches')) notes.push(`${shownPairs(flows).length} of ${rankedPairs(flows).length} country pairs`);
  return notes;
}

/** Only the marks of the layers that are on, in the colours the layers use. */
export function GeoLegend({ visible, flows }: { readonly visible: ReadonlySet<LayerId>; readonly flows: GeoFlows | null }) {
  const kinds = flows ? drawnKinds(flows) : new Set<string>();
  const keys = KEYS.filter((k) => visible.has(k.layer) && (k.kind === undefined || kinds.has(k.kind)));
  const notes = drawnCounts(flows, visible);
  if (keys.length === 0) return null;
  return (
    <div className="hidden w-56 border border-cx-line bg-white/95 p-2.5 text-label text-cx-ink-soft shadow-md sm:block">
      <ul aria-label="Map legend" className="space-y-1.5">
        {keys.map((k) => (
          <li key={k.label} className="flex items-center gap-2">
            <span aria-hidden="true" className={`inline-block w-4 shrink-0 ${k.swatch}`} />
            {k.label}
          </li>
        ))}
      </ul>
      {notes.length > 0 && <p className="mt-2 border-t border-cx-line-soft pt-1.5 text-cx-muted">Showing {notes.join(' · ')}</p>}
    </div>
  );
}
