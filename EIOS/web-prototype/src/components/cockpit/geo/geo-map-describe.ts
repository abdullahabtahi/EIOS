import { drawnCounts } from './geo-legend';
import { viewOf, type ViewId } from './geo-views';
import type { GeoFlows, GeoSelection, LayerId } from './geo-types';

const SELECTION_WORD = { corridor: 'corridor', mismatch: 'login pair', gateway: 'shared exit', account: 'account', country: 'country' } as const;

/** A pick in words: a route reads "NO to IR", anything else keeps its id. */
function pickedText(selection: NonNullable<GeoSelection>): string {
  const id = selection.kind === 'corridor' || selection.kind === 'mismatch' ? selection.id.split('>').join(' to ') : selection.id;
  return `${SELECTION_WORD[selection.kind]} ${id}`;
}

/**
 * What the map shows, as one short text for a screen reader. The map is drawn pixels, so this is the only way to know
 * what is on it; the counts come from the same ranking as the legend, and the keyboard route (the list, then the
 * assistant) is named because the marks themselves cannot be tabbed to.
 */
export function describeMap(view: ViewId, visible: ReadonlySet<LayerId>, flows: GeoFlows | null, selection: GeoSelection): string {
  const counts = drawnCounts(flows, visible);
  const drawn = counts.length > 0 ? `Showing ${counts.join(' and ')}.` : 'Countries are shaded by the list in view.';
  const picked = selection ? `Picked: ${pickedText(selection)}.` : 'Nothing is picked.';
  return `${viewOf(view).label} map. ${drawn} ${picked} Move through what is drawn with the list beside the map; press slash to ask the assistant. With the map itself focused, arrow keys pan it and plus and minus zoom.`;
}
