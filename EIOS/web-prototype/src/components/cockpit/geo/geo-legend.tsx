import * as React from 'react';
import { Icon } from '@/components/ui/icon';
import { OFFSHORE_NOTICE } from './geo-format';
import { BASEL_BREAKS, type BasisId } from './geo-basis';
import { drawnKinds, rankedCorridors, rankedPairs, shownCorridors, shownPairs } from './geo-rank';
import type { GeoFlows, LayerId } from './geo-types';

interface Key {
  readonly layer: LayerId;
  /** For risk-area keys: the list that colours the map, so the legend names only the marks in use. */
  readonly basis?: BasisId;
  /** For corridor keys: the kind of arc, so a colour that is not on the map is not in the legend. */
  readonly kind?: 'high' | 'medium' | 'other';
  readonly swatch: string;
  readonly label: string;
}

const KEYS: readonly Key[] = [
  { layer: 'risk', basis: 'fatf', swatch: 'h-3 bg-cx-bad/30 border border-cx-bad', label: 'FATF call for action' },
  { layer: 'risk', basis: 'fatf', swatch: 'h-3 bg-cx-warn/30 border border-cx-warn', label: 'FATF increased monitoring' },
  { layer: 'risk', basis: 'eu', swatch: 'h-3 bg-cx-warn/30 border border-cx-warn', label: 'On the EU high-risk list' },
  { layer: 'risk', basis: 'basel', swatch: 'h-3 bg-cx-bad/30 border border-cx-bad', label: `Higher risk (above ${BASEL_BREAKS.higher})` },
  { layer: 'risk', basis: 'basel', swatch: 'h-3 bg-cx-warn/30 border border-cx-warn', label: `Medium risk (${BASEL_BREAKS.medium} to ${BASEL_BREAKS.higher})` },
  { layer: 'risk', basis: 'basel', swatch: 'h-3 bg-slate-400/30 border border-slate-400', label: `Lower risk (below ${BASEL_BREAKS.medium})` },
  { layer: 'risk', basis: 'basel', swatch: 'h-3 border border-dashed border-cx-line', label: 'No fill: not in the public index' },
  { layer: 'offshore', swatch: 'h-3 bg-cx-muted/60 rounded-full', label: 'Offshore entities (size = count)' },
  { layer: 'corridors', kind: 'high', swatch: 'h-0.5 bg-cx-bad', label: 'High-risk corridor' },
  { layer: 'corridors', kind: 'medium', swatch: 'h-0.5 bg-cx-warn-solid', label: 'Medium-risk corridor' },
  { layer: 'corridors', kind: 'other', swatch: 'h-0.5 bg-cx-faint', label: 'Other corridor' },
  { layer: 'mismatches', swatch: 'h-0.5 bg-cx-ink', label: 'Registered here, logging in there' },
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
/** Outlines for the countries a list's latest change names, drawn on the map whenever the list has one. */
export interface ChangeOutlines {
  readonly added: boolean;
  readonly removed: boolean;
}

export function GeoLegend({ visible, flows, basis = 'fatf', outlines = null }: { readonly visible: ReadonlySet<LayerId>; readonly flows: GeoFlows | null; readonly basis?: BasisId; readonly outlines?: ChangeOutlines | null }) {
  // Below the small breakpoint the key is a line you open: dropping it would leave the colours unexplained.
  const [open, setOpen] = React.useState(false);
  const kinds = flows ? drawnKinds(flows) : new Set<string>();
  const keys = KEYS.filter((k) => visible.has(k.layer) && (k.basis === undefined || k.basis === basis) && (k.kind === undefined || kinds.has(k.kind)));
  const notes = drawnCounts(flows, visible);
  if (keys.length === 0 && !(outlines && visible.has('risk') && (outlines.added || outlines.removed))) return null;
  const shown = open ? 'block' : 'hidden sm:block';
  return (
    <div className="w-56 max-sm:w-auto max-sm:max-w-[calc(100vw-5rem)] border border-cx-line bg-white text-label text-cx-ink-soft">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="pointer-events-auto flex w-full cursor-pointer items-center gap-1.5 px-2.5 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cx-accent sm:hidden">
        <Icon icon={open ? 'expand_more' : 'expand_less'} size="sm" className="shrink-0 text-cx-muted" />
        <span className="font-semibold text-cx-ink">Key</span>
        {notes.length > 0 && <span className="min-w-0 truncate text-cx-muted">Showing {notes.join(' · ')}</span>}
      </button>
      <div className={`p-2.5 max-sm:pt-0 ${open ? '' : 'max-sm:hidden'}`}>
        <ul aria-label="Map legend" className={`${shown} space-y-1.5`}>
          {keys.map((k) => (
            <li key={k.label} className="flex items-center gap-2">
              <span aria-hidden="true" className={`inline-block w-4 shrink-0 ${k.swatch}`} />
              {k.label}
            </li>
          ))}
          {outlines && visible.has('risk') && outlines.added && (
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="inline-block h-3 w-4 shrink-0 border-2 border-cx-bad" />
              Added to the list
            </li>
          )}
          {outlines && visible.has('risk') && outlines.removed && (
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="inline-block h-3 w-4 shrink-0 border-2 border-cx-accent" />
              Removed from the list
            </li>
          )}
        </ul>
        <div data-legend-notes className={`${shown} space-y-1.5`}>
          {visible.has('corridors') && flows && <p className="mt-2 border-t border-cx-line-soft pt-1.5 text-cx-muted">A line darkens toward where the money goes. A ring marks where several routes meet.</p>}
          {visible.has('offshore') && <p className="mt-2 border-t border-cx-line-soft pt-1.5 text-cx-muted">{OFFSHORE_NOTICE}</p>}
        </div>
        {notes.length > 0 && <p className="mt-2 hidden border-t border-cx-line-soft pt-1.5 text-cx-muted sm:block">Showing {notes.join(' · ')}</p>}
      </div>
    </div>
  );
}
